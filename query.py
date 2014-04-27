#!/bin/python

import urllib2
import json

address_url = "http://blockchain.info/address/%s?format=json"

class Address:
	def __init__(self,address,tx=None):
		self.address = address
		self.total_received = None
		self.balance = None
		self.tx = tx

		self.sends_to = set()
		self.receives_from = set()

	def fill_tx(self):
		if self.tx == None:
			self.tx = get_tx_list(self.address)
	
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

def get_tx_list(address):
	data = json.load(urllib2.urlopen(address_url % address))
	txs = []
	for tx in data["txs"]:
		txs.append(TX(tx["hash"],
			map(lambda j:(j["prev_out"]["addr"],j["prev_out"]["value"]),tx["inputs"]),
			map(lambda j:(j["addr"],j["value"],reverse_spent(j["spent"])),tx["out"])))
	return txs

def explore(address,layers=1,forward=True,explored={}):
	root = Address(address)
	root.fill_tx()
	root.calc()
	explored[address] = root

	if layers == 0:
		return explored
	elif forward == True:
		for out in root.sends_to:
			if out not in explored:
				explore(out,layers-1,forward,explored)
	elif forward == False:
		for input in root.receives_from:
			if input not in explored:
				explore(input,layers-1,forward,explored)
	return explored

#takes a list of transactions, builds json to represent this list for our graph
def format_nodes(transactions):
	#transactions is a list of TX objects
	#positions is going to map addresses to places in our node list
	at = 0
	positions = {}
	#occurs will keep track of how many links each node is involved in, this comes into play with size
	occurs = {}
	#build the nodes
	nodes = []
	for tx in transactions:
		addresses = tx.inputs + tx.outputs
		for data in addresses:
			addr = data[0]
			if addr not in positions:
				#add index so we have it for later
				positions[addr] = at
				at += 1
				#update occurances
				occurs[addr] = 1
			else:
				occurs[addr] = occurs[addr] + 1
	#build the nodes themselves
	for addr in occurs:
		#make the actual node
		temp = {}
		temp['address'] = addr
		temp['size'] = occurs[addr]
		nodes.append(temp)
	#now build the links
	links = []
	for tx in transactions:
		for data in tx.inputs:
			sender = data[0]
			for data in tx.outputs:
				receiver = data[0]
				#get index of sender and receiver
				sender_ind = positions[sender]
				receiver_ind = positions[receiver]
				#make link from indexes
				link = {}
				link['source'] = sender_ind
				link['target'] = receiver_ind
				links.append(link)

	#build final graph
	graph = {}
	graph['nodes'] = nodes
	graph['links'] = links

	#dump json
	print json.dumps(graph, separators=(',',': '))
		

