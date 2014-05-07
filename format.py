import json
import math
import logging

#takes a list of transactions, builds json to represent this list for our graph
def transactions_to_graph(transactions):
	#transactions is a list of TX objects
	#positions is going to map addresses to places in our node list
	at = 0
	positions = {}
	#occurs will keep track of how many links each node is involved in, this comes into play with size
	occurs = {}
	#build the nodes
	nodes = []
	for tx in transactions:
		seen = set([])
		for data in tx.inputs:
			sender = data[0]
			for data in tx.outputs:
				receiver = data[0]
				test = (sender, receiver)
				if (sender, receiver) in seen:
					continue
				seen.add((sender, receiver))
				if sender not in occurs:
					occurs[sender] = 1
				else:
					occurs[sender] = occurs[sender] + 1
				if receiver not in occurs:
					occurs[receiver] = 1
				else:
					occurs[receiver] = occurs[receiver] + 1
		# seen = set([])
		# addresses = tx.inputs + tx.outputs
		# for data in addresses:
		# 	addr = data[0]
		# 	if addr not in occurs:
		# 		#update occurances
		# 		occurs[addr] = 1
		# 	# elif addr not in seen:
		# 	else:
		# 		occurs[addr] = occurs[addr] + 1
			# seen.add(addr)
	#build the nodes themselves
	# print occurs
	for addr in occurs:
		#add index so we have it for later
		positions[addr] = at
		at += 1
		#make the actual node
		temp = {}
		temp['address'] = addr
		temp['size'] = occurs[addr]
		nodes.append(temp)
	#now build the links
	links = []
	#for finding multiple links between 2 nodes
	found = {}
	for tx in transactions:
		seen = set([])
		for data in tx.inputs:
			sender = data[0]
			for data in tx.outputs:
				receiver = data[0]
				test = (sender, receiver)
				if (sender, receiver) in seen:
					continue
				seen.add((sender, receiver))
				#get index of sender and receiver
				sender_ind = positions[sender]
				receiver_ind = positions[receiver]
				#make link from indexes
				link = {}
				link['source'] = sender_ind
				link['target'] = receiver_ind
				if sender_ind < receiver_ind:
					tup = (sender_ind, receiver_ind)
				else:
					tup = (receiver_ind, sender_ind)
				if tup in found:
					found[tup] = found[tup] + 1
				else:
					found[tup] = 1
				link['linkNum'] = found[tup]
				links.append(link)

	#build final graph
	graph = {}
	graph['nodes'] = nodes
	graph['links'] = links

	#dump json
	return json.dumps(graph, separators=(',',': '))


def addrs_to_graph(addresses, direction):
	at = 0
	node_map = {}
	nodes = []
	for addr in addresses.itervalues():
		node = {}
		node['address'] = addr.address
		logging.debug(addr.get_received())
		node['label'] = addr.label
		node['classification'] = addr.classified_as
		node['total_received'] = addr.total_received
		node['size'] = math.log(addr.total_received)
		node['total_sent'] = addr.total_sent
		node['balance'] = addr.balance
		node_map[addr.address] = at
		at += 1
		nodes.append(node)
	links = []
	for addr in addresses.itervalues():
		if (direction == 1):
			to_explore = addr.sends_to
		elif (direction == 2):
			to_explore = addr.receives_from
		else:
			to_explore = addr.sends_to
		for connect in to_explore:
			if connect not in node_map:
				node = {'address': connect, 'size': 8, 'label':""}
				nodes.append(node)
				node_map[connect] = at
				at += 1
			link = {}
			sender = node_map[addr.address]
			target = node_map[connect]
			link['source'] = sender
			link['target'] = target
			links.append(link)
	graph = {'nodes': nodes, 'links': links}

	return json.dumps(graph, separators=(',',': '))

#takes a list of addresses, and simply formats them as a list of nodes
def format_entity(addresses):
	nodes = []
	for addr in addresses.itervalues():
		node = {'address': addr.address, 'label': addr.label}
		nodes.append(node)

	graph = {'nodes': nodes}

	logging.debug('returning')
	logging.debug(graph)

	return json.dumps(graph, separators=(',',': '))

