import query

def main():
	res = query.explore("13x2FVN4N6ahtbWCthKF3cArxrH9GJMNPg",layers=2)

	for addr in res.itervalues():
		print addr.address
		print "sends to: "+", ".join(addr.sends_to)
		print "receives from: "+", ".join(addr.receives_from)
		print "balance: "+str(addr.balance)


if __name__ == "__main__":
	main()
