import json
import math
import logging

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
			link = {'valueTo': 0, 'valueFrom': 0}
			sender = node_map[addr.address]
			target = node_map[connect]
			for tx in addr.tx:
				val = tx.address_balance(connect)
				if val > 0:
					link['valueTo'] += val
				elif val < 0:
					link['valueFrom'] += val

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

