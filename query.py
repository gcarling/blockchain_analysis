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

def round_numbers(root,address):
	amount = -1
	for tx in root.tx:
		outputs = []
		the_output = -1
		for out in tx.outputs:
			if out[0] == address:
				the_output = out[1]
			else:
				outputs.append(out[1])
		if more_round(the_output,outputs):
			return True

	return False

def more_round(num,list_of_num):
	# return if that number has a higher percentage of zeros than the other numbers
	return sorted(list_of_num+[num], key=lambda a:len(str(a).rstrip('0'))*1.0/len(str(a)))[0] == num

def explore(address,layers=1,max_nodes=None,forward=True,predicate=(lambda a,b:True),explored={}):
	root = Address(address)
	root.fill_tx()
	root.calc()
	explored[address] = root

	if (max_nodes == None and layers == 0) or (len(explored) >= max_nodes):
		return explored
	elif forward == True:
		for out in root.sends_to:
			if out not in explored and predicate(root,out):
				explore(out,layers-1,max_nodes=max_nodes,forward=forward,explored=explored)
	elif forward == False:
		for inp in root.receives_from:
			if inp not in explored and predicate(root,inp):
				explore(inp,layers-1,max_nodes=max_nodes,forward=forward,explored=explored)

	return explored
