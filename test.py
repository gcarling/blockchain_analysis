import query
import format

def main():
	res = query.explore("13x2FVN4N6ahtbWCthKF3cArxrH9GJMNPg",layers=2)


	transactions = []
	for addr in res.itervalues():
		# print addr.address
		# print "sends to: "+", ".join(addr.sends_to)
		# print "receives from: "+", ".join(addr.receives_from)
		# print "balance: "+str(addr.balance)
		for tx in addr.tx:
			transactions.append(tx)
			
	format.transactions_to_graph(transactions)

if __name__ == "__main__":
	main()
