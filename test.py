import query

def main():
	res = query.get_tx_list("1PXT49LGmJMWHGGtUi8nn83s2D8mANbsm1")

	for tx in res:
		print tx.id
		print tx.inputs
		print tx.outputs

if __name__ == "__main__":
	main()
