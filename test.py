import query
import format

def main():
	

	# res = query.explore("13x2FVN4N6ahtbWCthKF3cArxrH9GJMNPg",layers=2
	res = query.explore("1JSmxh6JofW5jcQBeQiR1M4XRhYqMET4Ck",layers=1);

	# res = query.explore(max_nodes=10,predicate=query.round_numbers)

	transactions = []
	for addr in res.itervalues():
		# print addr.address
		# print "sends to: "+", ".join(addr.sends_to)
		# print "receives from: "+", ".join(addr.receives_from)
		# print "balance: "+str(addr.balance)
		for tx in addr.tx:
			transactions.append(tx)

	print format.addrs_to_graph(res)

def group_entity():

	

	for addr in res.itervalues():
		print addr.tx

if __name__ == "__main__":
	main()
