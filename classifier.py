class Type:
	single_use = "single_use"
	hot_storage = "hot_storage"
	cold_storage = "cold_storage"
	mining_pool = "mining_pool"
	mining_solo = "mining_solo"
	faucet = "faucet"
	distributor = "distributor"

	unknown = "unknown"

class PredicatesC:

	def has_mined(self, address):
		"""
		returns
			0 never directly mined
			1 mined an entire block
			2 jointly mined a block
		"""
		for tx in address.tx:
			if len(tx.inputs) == 0:
				if len(tx.outputs) == 1:
					return 1
				else:
					return 2
		return 0

	def tx_balance(self, address):
		"""
		returns txs paying in / txs paying out
		"""
		in_count = 0.0
		out_count = 0.0
		for tx in address.tx:
			if tx.address_balance(address.address) > 0:
				in_count += 1
			else:
				out_count += 1

		if out_count == 0:
			return (10000, in_count, 0)
		return (in_count / out_count, in_count, out_count)

	def outputs_balance(self, address):
		"""
		returns number of outputs paying in / number of outputs paying out
		"""
		in_count = 0.0
		out_count = 0.0
		for tx in address.tx:
			if tx.address_balance(address.address) > 0:
				in_count += len(tx.inputs)
			else:
				out_count += len(tx.outputs)

		if out_count == 0:
			return (10000, in_count, 0)
		return (in_count / out_count, in_count, out_count)

	def pays_with_others(self,address):
		"""
		returns whether transactions have been sent using this address and another
		"""
		for tx in address.tx:
			i = set(map(lambda a:a[0], tx.inputs))
			if address.address in i and len(i) > 1:
				return True
		return False

	def total_satoshimilliseconds(self,address):
		"""
		returns total satoshi-milliseconds
		"""
		t = 0
		holding = 0
		sm = 0
		for tx in address.tx[::-1]:
			sm += holding * (tx.time - t)
			t = tx.time
			holding += tx.address_balance(address.address)
		return sm

	def average_payout_per_output(self,address):
		all_out = 0.0
		num_outputs = 0.0
		for tx in address.tx:
			b = tx.address_balance(address.address)
			if b < 0:
				all_out += abs(b)
				num_outputs += len(tx.outputs)
		if num_outputs == 0:
			return 10000
		return all_out / num_outputs

Predicates = PredicatesC()
predicates = [Predicates.has_mined,
				Predicates.tx_balance,
				Predicates.outputs_balance,
				Predicates.pays_with_others,
				Predicates.total_satoshimilliseconds,
				Predicates.average_payout_per_output]

def extract_features(address):

	return map(lambda a:a(address), predicates)

def decision_tree(address):

	m = Predicates.has_mined(address)

	if m == 1:
		return Type.mining_solo
	elif m == 2:
		return Type.mining_pool
	else:
		tx_b = Predicates.tx_balance(address)
		out_b = Predicates.outputs_balance(address)
		paying_with_friends = Predicates.pays_with_others(address)
		avg_out = Predicates.average_payout_per_output(address)

		if tx_b[0] == 1 and tx_b[1] == 1 and not paying_with_friends:
			return Type.single_use
		else:

			if len(address.tx) > 10 and out_b[0] < 0.4: #more than 4x tx sending than receiving
				if avg_out < 100000:
					return Type.faucet
				else:
					return Type.distributor
			elif out_b[0] == 10000 or (out_b[0] > 2 and tx_b[0] > 2 and address.get_balance() == 0):
				return Type.cold_storage

			else:
				return Type.hot_storage	
			
			#	Predicates.total_satoshimilliseconds

def tests():
	# 13x9weHkPTFL2TogQJz7LbpEsvpQJ1dxfa -> faucet
	# 1Fd5WNvXE3nx9W9nr3gWzuEqELH9R4xGmZ -> solo_mine
	# 1CwrK8GTwq4eQYZwTxMpL271Bpj7Zu3PUQ -> distribute
	# 1H5pwj5uZ2jjUwU2EcUuSvyR8Z5aAWU4ZY -> single_use
	# 1BuLgRGJdZzCfkWaKcxiTEL1ASqTFjt2Wf -> hot_storage
	pass

def classify(address):

	#features = extract_features(address)

	return decision_tree(address)