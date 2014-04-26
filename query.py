#!/bin/python

import urllib2
import json

address_url = "http://blockchain.info/address/%s?format=json"

class TX:
	def __init__(self,id,inputs,outputs):
		self.id = id
		self.inputs = inputs
		self.outputs = outputs

def reverse_spent(val):
	return "true" if val == "false" else "false"

def get_tx_list(address):
	data = json.load(urllib2.urlopen(address_url % address))
	for tx in data["txs"]:
		yield TX(tx["hash"],
			map(lambda j:(j["prev_out"]["addr"],j["prev_out"]["value"]),tx["inputs"]),
			map(lambda j:(j["addr"],j["value"],reverse_spent(j["spent"])),tx["out"]))
