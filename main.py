
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
import logging
import time
import zlib

# local files
import classifier
import format
# end local

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
		self.total_sent = None
		self.balance = None
		self.tx = tx

		self.sends_to = set()
		self.receives_from = set()

		self.classified_as = -1
		self.label = ""

		self.status = 0 # 0 is hasn't begun, 1 is fetch, 2 is ready

	def fill_tx(self, direction=0):
		if self.status == 1:
			return -1
		self.status = 1

		if self.tx == None:
			self.tx = get_tx_list(self.address)
			self.status = 2
	
	def get_balance(self):
		if self.balance == None:
			if self.calc() == -1:
				return -1
		return self.balance

	def get_received(self):
		if self.balance == None:
			if self.calc() == -1:
				return -1
		return self.total_received

	def calc(self):
		if self.tx == None:
			if self.fill_tx() == -1:
				return -1

		data = check_cache(self.address)

		self.label = get_label(self.address)
		self.balance = data["final_balance"]
		self.total_received = data["total_received"]
		self.total_sent = data["total_sent"]
		for t in self.tx:
			type = (reduce((lambda a,b:a or b[0]==self.address),t.inputs,False),
						reduce((lambda a,b:a or b[0]==self.address),t.outputs, False))

			logging.debug(type)
			for i in t.inputs:
				if i[0] == self.address:
					self.balance -= abs(i[1])
				elif type[1]:
					self.receives_from.add(i[0])
			for i in t.outputs:
				if i[0] == self.address:
					self.balance += abs(i[1])
					self.total_received += abs(i[1])
				elif type[0]:
					self.sends_to.add(i[0])
		
		self.classified_as = classifier.classify(self)

class TX:
	def __init__(self,id,inputs,outputs,time):
		self.id = id
		self.inputs = inputs
		self.outputs = outputs
		self.time = int(time)

	def address_balance(self, address):
		balance = 0
		for i in self.inputs:
			if i[0] == address:
				balance -= abs(i[1])
		for i in self.outputs:
			if i[0] == address:
				balance += abs(i[1])
		return balance

def reverse_spent(val):
	return "true" if val == "false" else "false"

def check_cache(address):
	c = CachedRequest.gql("WHERE address = :1", address).get()
	if c:
		while not c.data:
			time.sleep(0.5)
			c = CachedRequest.gql("WHERE address = :1", address).get()
		#data = zlib.decompress(c.data.encode("utf-8"))
		data = c.data
	else:
		c = CachedRequest()
		c.address = address
		c.put()
		data = urlfetch.fetch(address_url % address).content
		#c.data = zlib.compress(data.encode("utf-8"))
		c.data = data
		c.put()

	data = json.loads(data)
	return data

def get_label(address):
	data = check_cache(address)

	if (len(data["txs"]) > 0):
		for t in data["txs"]:
			for o in t['out']:
				if "addr_tag" in o and o["addr"] == address:
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
			map(lambda j:(j["addr"],j["value"],reverse_spent(j["spent"])),tx["out"]),tx["time"]))
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

def explore(address,layers=1,max_nodes=None,direction=0,predicate=(lambda a,b:True),explored=0,log=(lambda a:0)):
	"""
		returns list of addresses visited, each with addr.tx

		direction:
			0: go both forwards and backwards
			1: go forwards only
			2: go backwards only
	"""
	if explored==0: explored = {}

	log = (lambda a:0)

	log(str(direction))

	logging.debug(explored)

	root = Address(address)
	root.fill_tx(direction=direction)
	root.calc()
	explored[address] = root

	log("%s : %d" % (address, layers))
	#log(str(root.sends_to))
	#log(str(root.receives_from))

	if (max_nodes == None and layers == 0) or (max_nodes != None and len(explored) >= max_nodes):
		log("exiting with max_nodes: %s and layers: %d and len(explored): %d" % (str(max_nodes), layers, len(explored)))
		logging.debug(explored)
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
			if self.request.get("type") == "entity":
				res = explore(self.request.get("address") or "13dXiBv5228bqU5ZLM843YTxT7fWHZQEwH",log=(lambda a:self.response.out.write(a+"<br/>")),max_nodes=(int(self.request.get("max_nodes")) or 10),predicate=follow_entity,direction=(int(self.request.get("direction")) or 0))
			else:
				if self.request.get("layers") != None:
					num_layers = int(self.request.get("layers"))
				else:
					num_layers = 2
				res = explore(self.request.get("address") or "13x2FVN4N6ahtbWCthKF3cArxrH9GJMNPg",log=(lambda a:self.response.out.write(a+"<br/>")),layers=(num_layers),direction=(int(self.request.get("direction")) or 0),explored={})
		except ValueError:
			return self.response.out.write("Error: bad arguments")

		#for addr in res.itervalues():
		#	for tx in addr.tx:
		#		transactions.append(tx)

		if self.request.get("type") == "entity":
			self.response.out.write(format.format_entity(res))
		else:
			self.response.out.write(format.addrs_to_graph(res))

class TempHandler(webapp2.RequestHandler):
    def get(self):
        self.response.out.write(graph_json.render({}))

class TestHandler(webapp2.RequestHandler):
	def get(self):

		addresses = ["1FmEPt4auamXQiCs3wBhzduinPA48uGgx3"]
		expected = [("1FmEPt4auamXQiCs3wBhzduinPA48uGgx3",0,122177650,["175fDz6KqRRaxQHEGyCKrLNTKeeQgBvmxc"],["18iegfRPbn2JD2HF6GPMBRZ97tW8V17fPu","1E3LBRx8RDxQrpGDSiWk3yAF7yDHXuuQUL"])]

		for i in range(0,len(addresses)):
			output = explore(addresses[i], layers=0, direction=0)[addresses[i]]

			self.response.out.write("expecting %s got %s <br/>" % (expected[i][0], output.address))
			self.response.out.write("expecting %d got %s <br/>" % (expected[i][1], output.get_balance()))
			self.response.out.write("expecting %d got %s <br/>" % (expected[i][2], output.get_received()))
			self.response.out.write("expecting %s got %s <br/>" % (str(expected[i][3]), str(output.receives_from)))
			self.response.out.write("expecting %s got %s <br/>" % (str(expected[i][4]), str(output.sends_to)))
			self.response.out.write("--")

class ClassifyHandler(webapp2.RequestHandler):
	def get(self, addr):
		a = Address(addr)
		a.calc()
		self.response.out.write(classifier.classify(a))
		self.response.out.write("<br/>")
		self.response.out.write(classifier.extract_features(a))

app = webapp2.WSGIApplication([
    ('/', MainHandler),
	('/data', DataHandler),
	('/tests', TestHandler),
	('/classify/(.*?)', ClassifyHandler),
	('/graph.json', TempHandler)
], debug=True)
