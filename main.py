#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
import json
from google.appengine.api import urlfetch
from google.appengine.ext import db
import format
import logging

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])
graph_template = JINJA_ENVIRONMENT.get_template('explorer.html')
graph_json = JINJA_ENVIRONMENT.get_template('graph.json')

class CachedRequest(db.Model):
	address = db.StringProperty()
	data = db.TextProperty()

address_url = "http://blockchain.info/address/%s?format=json"

class Address:
	def __init__(self,address,tx=None):
		self.address = address
		self.total_received = None
		self.balance = None
		self.tx = tx
		self.label = ""

		self.sends_to = set()
		self.receives_from = set()

	def fill_tx(self, direction=0):
		if self.tx == None:
			self.tx = get_tx_list(self.address)

			for tx in self.tx:
				fine = False
				if direction == 0:
					fine = True
				if direction == 1: #no backwards, want tx with ourselves as sender
					for o in tx.inputs:
						if o[0] == self.address:
							fine = True
				elif direction == 2: #no forwards, want tx with ourselves as receiver
					for o in tx.outputs:
						if o[0] == self.address:
							fine = True
				if fine == False:
					self.tx.remove(tx)
	
	def balance(self):
		if self.balance == None:
			self.calc()
		return self.balance

	def received(self):
		if self.balance == None:
			self.calc()
		return self.total_received
		
	def calc(self):
		if self.tx == None:
			self.fill_tx()
		self.label = get_label(self.address)
		self.balance = 0
		self.total_received = 0
		for t in self.tx:
			type = (reduce((lambda a,b:a or b[0]==self.address),t.inputs,False),
					reduce((lambda a,b:a or b[0]==self.address),t.outputs, False))
			for i in t.inputs:
				if i[0] == self.address:
					self.balance -= i[1]
				elif type[1]:
					self.receives_from.add(i[0])
			for i in t.outputs:
				if i[0] == self.address:
					self.balance += i[1]
					self.total_received += i[1]
				elif type[0]:
					self.sends_to.add(i[0])

class TX:
	def __init__(self,id,inputs,outputs):
		self.id = id
		self.inputs = inputs
		self.outputs = outputs

def reverse_spent(val):
	return "true" if val == "false" else "false"

def check_cache(address):
	c = CachedRequest.gql("WHERE address = :1", address).get()
	if c:
		data = c.data
	else:
		data = urlfetch.fetch(address_url % address).content
		c = CachedRequest()
		c.address = address
		c.data = data
		c.put()

	data = json.loads(data)
	return data

def get_label(address):
	data = check_cache(address)

	if (len(data["txs"]) > 0):
		for o in data["txs"][0]['out']:
			if "addr_tag" in o and o["addr"] = address:
				return o["addr_tag"]

	return ""

def get_tx_list(address):
	# check cache
	data = check_cache(address)

	
	txs = []
	for tx in data["txs"]:
		if tx["inputs"][0] == {}:
			inputs = []
		else:
			inputs = map(lambda j:(j["prev_out"]["addr"],j["prev_out"]["value"]),tx["inputs"])
		txs.append(TX(tx["hash"],
			inputs,
			map(lambda j:(j["addr"],j["value"],reverse_spent(j["spent"])),tx["out"])))
	return txs

def follow_entity(root,address):
	#only accept nodes with a single outgoing tx, and take the address with the non-round number
	logging.debug(root.address)
	logging.debug(root.sends_to)
	logging.debug(address)
	if len(root.sends_to) != 2:
		return False
	amount = -1
	for tx in root.tx:
		for o in tx.outputs:
			if o[0] not in root.sends_to:
				continue
		outputs = []
		the_output = -1
		for out in tx.outputs:
			if out[0] == address:
				the_output = out[1]
			else:
				outputs.append(out[1])
		logging.debug("the: "+str(the_output))
		logging.debug("the: "+str(outputs))
		if more_round(the_output,outputs):
			logging.debug("is not followed")
			return False

	logging.debug("is followed")
	return True

def more_round(num,list_of_num):
	# return if that number has a higher percentage of zeros than the other numbers
	return sorted(list_of_num+[num], key=lambda a:len(str(a).rstrip('0'))*1.0/len(str(a)))[0] == num

def explore(address,layers=1,max_nodes=None,direction=0,predicate=(lambda a,b:True),explored={},log=(lambda a:0)):
	"""
		returns list of addresses visited, each with addr.tx

		direction:
			0: go both forwards and backwards
			1: go forwards only
			2: go backwards only
	"""

	log = (lambda a:0)

	log(str(direction))

	root = Address(address)
	root.fill_tx(direction=direction)
	root.calc()
	explored[address] = root

	log("%s : %d" % (address, layers))
	#log(str(root.sends_to))
	#log(str(root.receives_from))

	if (max_nodes == None and layers == 0) or (max_nodes != None and len(explored) >= max_nodes):
		log("exiting with max_nodes: %s and layers: %d and len(explored): %d" % (str(max_nodes), layers, len(explored)))
		return explored
	elif direction == 0 or direction == 1:
		for out in root.sends_to:
			if out not in explored and predicate(root,out) and not (max_nodes != None and len(explored) >= max_nodes):
				explore(out,layers-1,max_nodes=max_nodes,predicate=predicate,direction=direction,explored=explored,log=log)
	elif direction == 0 or direction == 2:
		for inp in root.receives_from:
			if inp not in explored and predicate(root,inp) and not (max_nodes != None and len(explored) >= max_nodes):
				explore(inp,layers-1,max_nodes=max_nodes,predicate=predicate,direction=direction,explored=explored,log=log)
	else:
		log("bad! direction is: %s" % str(direction))

	return explored	

class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.out.write(graph_template.render({}))

class DataHandler(webapp2.RequestHandler):
    def get(self):
		try:
			if self.request.get("layers") != None:
				num_layers = int(self.request.get("layers"))
			else:
				num_layers = 2
			if self.request.get("type") == "entity":
				res = explore(self.request.get("address") or "13dXiBv5228bqU5ZLM843YTxT7fWHZQEwH",log=(lambda a:self.response.out.write(a+"<br/>")),max_nodes=(int(self.request.get("max_nodes")) or 10),predicate=follow_entity,direction=(int(self.request.get("direction")) or 0))
			res = explore(self.request.get("address") or "13x2FVN4N6ahtbWCthKF3cArxrH9GJMNPg",log=(lambda a:self.response.out.write(a+"<br/>")),layers=(num_layers),direction=(int(self.request.get("direction")) or 0))
		except ValueError:
			return self.response.out.write("Error: bad arguments")

		#for addr in res.itervalues():
		#	for tx in addr.tx:
		#		transactions.append(tx)

		self.response.out.write(format.addrs_to_graph(response))

class TempHandler(webapp2.RequestHandler):
    def get(self):
        self.response.out.write(graph_json.render({}))

app = webapp2.WSGIApplication([
    ('/', MainHandler),
	('/data', DataHandler),
	('/graph.json', TempHandler)
], debug=True)
