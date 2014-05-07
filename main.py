
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
import random

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

class TooLargeError(Exception):
    pass

class NonStandardTransactionError(Exception):
	pass

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

			for i in t.inputs:
				if i[0] == self.address:
					pass
				elif type[1]:
					self.receives_from.add(i[0])
			for i in t.outputs:
				if i[0] == self.address:
					pass
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
	logging.debug("fetching "+address)
	c = CachedRequest.gql("WHERE address = :1", address).get()
	if c:
		while not c.data and not c.data == "":
			logging.debug("sleeping")
			time.sleep(0.5)
			c = CachedRequest.all(keys_only=True).filter('address',address)
			c = db.get(list(c))[0]
		#data = zlib.decompress(c.data)
		data = c.data
	else:
		c = CachedRequest()
		c.address = address
		c.put()
		data = urlfetch.fetch(address_url % address).content

		if len(data) > 900000:
			c.data = ""
			c.put()
			raise TooLargeError
		#c.data = zlib.compress(data.decode("utf-8"))
		c.data = data
		try:
			c.put()
		except:
			logging.debug("address: %s is too big (%d len), removing" % (address, len(c.data)))
			c.data = ""
			c.put()
			raise TooLargeError
			
	if data == "":
		raise TooLargeError

	try:
		data = json.loads(data)
	except ValueError:
		logging.debug("data is: "+str(data)+" "+str(address))

	logging.debug("success fetching.")
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
		try:
			txs.append(TX(tx["hash"],
				inputs,
				map(lambda j:(j["addr"],j["value"],reverse_spent(j["spent"])),tx["out"]),
				tx["time"]))
		except KeyError:
			#raise NonStandardTransactionError
			pass

	return txs

def transmit_more_than(root,address,amount):
	total = 0
	for tx in root.tx:
		for o in tx.outputs+tx.inputs:
			if o[0] == address:
				total += abs(o[1])
	return total > amount

def follow_entity(root,address):
	"""
	only accept nodes with a single outgoing tx, and take the address with the non-round number
	in addition, group all addresses that send in a shared transaction if one of the outputs is the same as one of the inputs
	"""
	logging.debug("should I follow %s ?" % address)
	for tx in root.tx:
		same = False
		for o in tx.outputs:
			for i in tx.inputs:
				if o[0] == i[0]:
					same = True
		if same == True:
			# all the inputs should be grouped
			for i in tx.inputs:
				if i[0] == address:
					logging.debug("yes! spent together")
					return True

	amount = -1
	for tx in root.tx:
		# TIL for else 
		for o in tx.outputs:
			if o[0] not in root.sends_to:
				break
		else:
			outputs = []
			the_output = -1
			for out in tx.outputs:
				if out[0] == address:
					the_output = out[1]
				else:
					outputs.append(out[1])
			if the_output == -1:
				continue
			logging.debug("the: "+str(the_output))
			logging.debug("the: "+str(outputs))
			if is_less_round(the_output,outputs):
				logging.debug("is followed")
				return True

	logging.debug("is not followed")
	return False

def is_less_round(num,list_of_num):
	# return if that number has a higher percentage of zeros than the other numbers
	percent_not_zeros = (lambda a:len(str(a).rstrip('0'))*1.0/len(str(a)))
	order = sorted(list_of_num+[num], key=percent_not_zeros)
	order.reverse()
	return order[0] == num and percent_not_zeros(str(num)+"0") > percent_not_zeros(str(order[1]))

def explore(address,layers=1,max_nodes=None,direction=0,predicate=(lambda a,b:True),mbtc_threshold=0.1,max_connections=10,explored=0):
	"""
		returns list of addresses visited, each with addr.tx

		direction:
			0: go both forwards and backwards
			1: go forwards only
			2: go backwards only
	"""
	if explored==0: explored = {}

	logging.debug(explored)

	try:
		root = Address(address)
		root.fill_tx(direction=direction)
		root.calc()
	except TooLargeError:
		logging.debug("caught too large, ignoring.")
		return explored

	explored[address] = root

	if (max_nodes == None and layers == 0) or (max_nodes != None and len(explored) >= max_nodes):
		logging.debug("exiting with max_nodes: %s and layers: %d and len(explored): %d" % (str(max_nodes), layers, len(explored)))
		return explored
	else:
		if direction == 0:
			comb = set(list(root.sends_to)+list(root.receives_from))
		elif direction == 1:
			comb = root.sends_to
		elif direction == 2:
			comb = root.receives_from
		else:
			logging.debug("bad! direction is: %s" % str(direction))
			comb = []
	
		if len(comb) <= max_connections:
			for x in comb:
				if predicate(root,x) and transmit_more_than(root,x,mbtc_threshold*100000):
					explore(x,layers-1,max_nodes=max_nodes,predicate=predicate,direction=direction,explored=explored)

	return explored	

class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.out.write(graph_template.render({}))

class DataHandler(webapp2.RequestHandler):
    def get(self):
		try:
			
			logging.debug("a")
			num_layers = int(self.request.get("layers")) or 0

			logging.debug("b")

			if self.request.get("type") == "entity":
				predicate = follow_entity
			else:
				predicate = (lambda a,b:True)

			direction = (int(self.request.get("direction")) or 0)

			logging.debug("c")

			logging.debug(self.request.get("max_connections"))
			logging.debug(self.request.get("mbtc_threshold"))
			if self.request.get("max_connections") not in [None,""]:
				max_connections = int(self.request.get("max_connections"))
			else:
				max_connections = 100

			logging.debug("d")

			if self.request.get("mbtc_threshold") not in [None,""]:
				mbtc_threshold = int(self.request.get("mbtc_threshold"))
			else:
				mbtc_threshold = 0.1

			logging.debug("e")

			res = explore(self.request.get("address") or "13dXiBv5228bqU5ZLM843YTxT7fWHZQEwH",max_connections=max_connections,mbtc_threshold=mbtc_threshold,layers=num_layers,predicate=predicate,direction=direction)

		except ValueError:
			return self.response.out.write("Error: bad arguments")

		if self.request.get("type") == "entity":
			self.response.out.write(format.format_entity(res))
		else:
			self.response.out.write(format.addrs_to_graph(res, direction))

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

		self.response.out.write("<br/>")

		addresses = ["1DirtycatzdoC8u8DaMsVjWFfYvyzawCGe"]
		expected = [("1DirtycatzdoC8u8DaMsVjWFfYvyzawCGe","1GjV6jqBtER7B5Q4UxNhkNmnhyLZ2ypeuy","19ZPKhpcufZQWHKKhrte4ufvepg3ZG8Brp","1Bp6rSUS4GmraVYGRSeETeB1whMkJfp8hZ","19qMtjDT5b6pRPAXqwJDFQ6PMTfiTArGYt","17kNhYKkcyxFsorwD8dksZvsQjujJcCf1Z","1LFByrc6WfrfaRfmp8wpjXBxoQw2itv5ei",
						"15js7RpQBevVy1d7VWYSo9NYRKDhNf7Vzw","14y7c6VAEgjuzo8D23rKX5BCEe7yKJBh22","1DjMhkEZk8H7qurPWkZiJTfisj5ALBr3tD","1BUjnseABZWtJGhNwz5zyrzFqMK3HJJS4Y","1ADnvaeeDPnDsLHX4Rg7kvHUVHEs14uzYG","1DFs1qRe441YeEYA2yjY5R7BLJchmWEvER","13PeYCq85MAN8CHxEwu7d8zPMn8aFostjW","1GVoc5hXwuswj6A6m3eovd1D3bjv5Wu1VP","1EeXLmMsib7Ln9GvjnhcLEzFjRCzzSdyqi","1LkXuX8VcGZcYJpPcZsD3WsWecUenMatBq","12m2ZKZdVv6bkJ4NxxpyLEroSRjw297m6G","1NxA9vmKfc4NQNDWRb81F6RBsdKSwX7upP","1NeyQ3Gz9XtDwZHLYPzGYEFYib5U6VWfBv","1NdExDKxy9UGgZFvWoLKryEDSLkvHiGqnN","15cLKc9SNL1AKe1e3yLKVCJ4CAMaqUmLM7","1LUu63oqAjHQSucVXYuuHJTrsd2D2GrFhe","1Ct15pzWFdZ9RvRdHVYNuFwXJA4qkR6owT","1J6qgkYcWWeyLr1AWTaBNtPNaQAHsc8x15", #""" 1H2kqMswmtrJUpGbAttDiLdn7aYnDMfjLd","13fvixKe9frKEawS6LWSBCTjMp8LEDoycv","1CKGKgUUyDRF3CBaz6YetMWiVGgmCC8Sm","16ppeDthYK6LNsnDTaHwHjSBEEt2FGQYmS","1PyqEcgBDMUfhYbxr9NfYkodTEwJQzFPtR","18gfVvp6cqPZgYwNMPvsPnsUGgUhxz5zzf","182N4weu7XGPmuc2GbswokYarq7r8rduWu","1PP8sWacFGepmQb7q71vvo1VkgUewWsTzd","198mPEzm9b3nDzgua47RtnyNTSUnfWySxh","1BoPpbRBBNvXWTGBiPQbSAfmVnvoaJMiBr","15UceBucJG8LEcPpHcPzQ2AcfTmfHr8Dv2","1LvwcupsBDAgayguzMHGGgw6HZy9a3Kanp","1EqiGFRXgBtwnuNzTULkgVUdBnjm9vK3XD","1LREyMuxP5akkkWVCew7nbJXJFzuQpGBZn", """ #past 50 tx mark
						"1KLL4Xhxxi3Nviwr1Qzz1A5tgGeA3DNZKs",
						"19TptEheMnzUtpX3thpEbNjttKY8aXCKqk")]

		for i in range(0,len(addresses)):
			output = explore(addresses[i], layers=1, predicate=follow_entity, direction=0)

			e = list(expected[i])
			for addr in output.iterkeys():
				if addr in e:
					self.response.out.write("expected and got: %s <br/>" % addr)
					e.remove(addr)
				else:
					self.response.out.write("got unexpected: %s <br/>" % addr)
			self.response.out.write("--<br/>")
			for a in e:
				self.response.out.write("expected but didn't get: %s<br/>" % a)


class MassGroupHandler(webapp2.RequestHandler):
	def get(self):
		self.response.out.write("loading")
		if self.request.get("set")=="large":
			f = open('tags.tsv','r').read().split("\n")
		else:
			f = open('tags_small.tsv','r').read().split("\n")
		self.response.out.write("loaded tags")
		out = {}
		for g in f:
			g = g.split("\t")
			if g[0][0] != "1":
				continue
			out[g[0]] = [[],[]]
			addrs = explore(g[0],max_nodes=10,predicate=follow_entity,direction=0)
			for a in addrs.itervalues():
				out[g[0]][0] += list(a.sends_to)
				out[g[0]][1] += list(a.receives_from)

		ii = {}

		for a,x in out.iteritems():
			for y in x[0]: #sends to = 0, =1
				if not y in ii:
					ii[y] = []
				ii[y].append(a)

		for a,x in ii.iteritems():
			if len(x) > 1:
				self.response.out.write(a+": "+str(x))

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
	('/graph.json', TempHandler),
	('/domass', MassGroupHandler)
], debug=True)
