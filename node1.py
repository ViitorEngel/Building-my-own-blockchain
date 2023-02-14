import hashlib
import json
from time import time
from uuid import uuid4
from textwrap import dedent
from flask import Flask, jsonify, request
from urllib.parse import urlparse

#let's tart by creating the blockchain object:
class Blockchain(object):
    def __init__(self):
        #storing the blockchain
        self.chain = []
        #storing transactions
        self.current_transactions = []
        #storing the nodes of the blockchain
        self_nodes = set()

        #we need to create the genesis bloack, the first block that is created in the chain
        self.new_block(previous_hash=1, proof=100)

    #this adds a new node to the blockchain, making it decentralized.
    def register_node(self, addres):
        parsed_url = urlparse(addres)
        self.nodes.add(parsed_url.netloc)

    #verifying if a given blockchain is valid by checking if every block has it hash and proof
    def valid_chain(self, chain):
        last_block = chain[0]
        current_index=1

        while current_index<len(chain):
            block=chain[current_index]
            print(f"{last_block}")
            print(f"{block}")
            print("\n---\n")
            
            if block['previous_hash'] != self.hash*(last_block):
                return False

            if not self.valid_proof(last_block["proof"],block["proof"]):
                return False

            last_block=block
            current_index+=1
        
        return True

    #the consensus algorithm, that replaces our chain with the longest one in the network, return True if it was replaced
    def resolve_conflicts(self):
        neighbours = self.nodes    
        new_chain=None

        for node in neighbours:
            response = request.get(f"http://{node}/chain")

            if response.status_code == 200:
                lenght = response.json()["lenght"]
                chain = response.json()["chain"]

                if lenght > max_lenght and self.valid_chain(chain):
                    max_lenght = lenght
                    new_chain = chain
        
        if new_chain:
            self.chain = new_chain
            return True

        return False

    #this method will create a new block and add to the blockchain
    def new_block(self, proof, previous_hash=None):
        block = {
            "index": len(self.chain) +1, #the index in the chain
            "timestamp": time(), #when it was created
            "transactions": self.current_transactions, #which transaction it is
            "proof": proof, #proof of work
            "previous_hash": previous_hash or self.hash(self.chain[-1]), #last block's hash
        }

        #reseting transactions
        self.current_transactions=[]

        #append the block to the chain
        self.chain.append(block)
        return block
    
    #this method will creade a new transaction to the list of transactions
    def new_transaction(self, sender, recipient, amount):
        #adding the transaction to the transactions dictionary
        self.current_transactions.append({
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
        })
        return self.last_block['index']+1

    #this will hash a block with sha-256 hash
    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    #this will return the lash block in the chain
    @property
    def last_block(self):
        return self.chain[-1]

    #creting a method that validates the proof
    #the proof will be to find an especific number that when hashed wit the last hash is going tho end in four zeros.
    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof
    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:3]=="000"

#Instantiate the node
app = Flask(__name__)

#generating an adrres for this node
node_identifier = str(uuid4()).replace('-','')

#instantiate the Blockchain
blockchain = Blockchain()

#determining the http methods
@app.route("/chain", methods=["GET"])
def full_chain():
    response={
        "chain": blockchain.chain,
        "length": len(blockchain.chain),
    }
    return jsonify(response),200

@app.route("/transactions/new", methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check the required fields 
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Creating transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work 
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We receive a reward
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the Block
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

#registering nodes
@app.route("/nodes/register", methods=["Post"])
def register_nodes():
    values = request.get_json

    nodes = values.get("nodes")
    if nodes is None:
        return "Error, we need a valid list of nodes", 400

        for node in nodes:
            blockchain.register_node(node)

        response = {
            "message":"New nodes added",
            "total_nodes":list(blockchain.nodes)
        }
        return jsonify(response),201

#resolving the nodes conflicts
@app.route("/nodes/resolve", methods=["GET"])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            "message":"Chain was replaced",
            "new_chain":blockchain.chain
        }
    else:
        response = {
            "message":"Our chain is the authoritative",
            "chain": blockchain.chain
        }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port = 5001) 