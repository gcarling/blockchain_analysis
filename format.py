import json
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


def addrs_to_graph(addresses):
	at = 0
	node_map = {}
	nodes = []
	for addr in addresses.itervalues():
		node = {}
		node['address'] = addr.address
		node['size'] = addr.total_received
		node_map[addr.address] = at
		at += 1
		nodes.append(node)
	links = []
	for addr in addresses.itervalues():
		for sent_to in addr.sends_to:
			if sent_to not in node_map:
				node = {'address': sent_to, 'size': 2}
				nodes.append(node)
				node_map[sent_to] = at
				at += 1
			link = {}
			sender = node_map[addr.address]
			target = node_map[sent_to]
			link['source'] = sender
			link['target'] = target
			links.append(link)
	graph = {'nodes': nodes, 'links': links}

	return json.dumps(graph, separators=(',',': '))


