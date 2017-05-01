import logging
import string
import random
import json
from block import Block
import os
import binascii
import hashlib
from Crypto.Cipher import AES
from Crypto import Random


class QuantCoin:
    '''
    QuantCoin is the main facade to the quantcoin node internal storage. All
    peers, blockchain are stored in a public databased, that is shared by the
    nodes in the network. The wallets are stored in a private database
    protected by a password only accessible by this node.
    '''

    def __init__(self):
        '''
        Instantiates a QuantCoin storage.
        '''
        self._blocks = []
        self._peers = [("127.0.0.1", 65345)]
        self._public_wallets = []
        self._wallets = []

    def load(self, database):
        '''
        Loads the public store from a file. The file is a JSON that represents
        the public storage of the network.

            database: path to the public storage JSON file.
        '''
        logging.debug("Loading from database")
        if os.path.exists(database):
            with open(database, 'rb') as fp:
                storage = json.load(fp)
                blocks = storage['blocks']
                self._blocks = [Block.from_json(block) for block in blocks]
                self._peers = [tuple(peer) for peer in storage['peers']]
                self._public_wallets = [tuple(public_wallet)
                                        for public_wallet
                                        in storage['public_wallets']]
        else:
            logging.debug("Requested database does not exists(database={})".
                          format(database))
            return False

    def save(self, database):
        '''
        Saves the public store to a file. The file will be saved in JSON
        format.

            database: path to the file.
        '''
        logging.debug("Saving to database")
        with open(database, 'wb') as fp:
            json_blocks = [block.json() for block in self._blocks]
            storage = {
                'blocks': json_blocks,
                'peers': self._peers,
                'public_wallets': self._public_wallets
                }
            json.dump(storage, fp)

    def load_private(self, database, password):
        '''
        Loads the private storage from a file. The file is in JSON format,
        protected by a password trought AES-256 encryption.

            database: path to the private storage.
            password: passoword to open the storage.

            returns: True if storage loaded correctly, False otherwise.
        '''
        logging.debug("Loading from private database")
        if os.path.exists(database):
            with open(database, 'rb') as fp:
                with open(database + '.iv') as fpiv:
                    iv = fpiv.read()
                aes = AES.new(hashlib.sha256(password).digest(),
                              AES.MODE_CBC, iv)
                storage_json = self.__unpad(aes.decrypt(fp.read()))
                try:
                    self._wallets = json.loads(storage_json)['wallets']
                    return True
                except Exception:
                    print("Your password is problably wrong!")
                    return False
        else:
            logging.debug("Requested private database " +
                          "does not exists(database={})".format(database))
            return False

    def save_private(self, database, password):
        '''
        Encripts the private store with AES-256 using the password for the
        key generation.

            database: the path to the file where the private store will be
                saved.
            password: the password used to generate the AES-256 key.
        '''
        logging.debug("Saving to private database")
        with open(database, 'wb') as fp:
            storage = {
                'wallets': self._wallets
            }
            storage_json = json.dumps(storage)
            iv = Random.new().read(AES.block_size)
            with open(database + ".iv", 'wb') as fpiv:
                fpiv.write(iv)
            aes = AES.new(hashlib.sha256(password).digest(), AES.MODE_CBC, iv)
            encrypted_storage = aes.encrypt(self.__pad(storage_json))
            fp.write(encrypted_storage)

    def __pad(self, m):
        '''
        Pads the message so it can be encrypted by AES-256.
        '''
        return m + (16 - len(m) % 16) * chr(16 - len(m) % 16)

    def __unpad(self, m):
        '''
        Remove the pad of a decrypted message.
        '''
        return m[0:-ord(m[-1])]

    def all_nodes(self):
        '''
        Obtains all peers known by this node.
        '''
        logging.debug("All nodes requested")
        return self._peers

    def blocks(self):
        '''
        Obtains the blockchain.
        '''
        logging.debug("All blocks requested")
        return self._blocks

    def block(self, start, end):
        '''
        Obtains part of the blockchain.

            start: the start point of blocks requested.
            end: the index of the last block requested.

        returns: a slice of the blockchain
        '''
        logging.debug("Block range requested(from={},to={})".
                      format(start, end))
        return self._blocks[start:end]

    def wallets(self):
        '''
        Obtains the wallets of this node.
        '''
        return self._wallets

    def public_wallets(self):
        '''
        Obtains the public keys for wallets.
        '''
        return self._public_wallets

    def store_wallet(self, wallet):
        '''
        Adds a new wallet to this node.
        '''
        if wallet not in self._wallets:
            self._wallets.append(wallet)

    def store_public_wallet(self, public_key):
        '''
        Stores the new wallet registered in the network.
        '''
        public_key_string = binascii.a2b_base64(public_key)
        address = "QC" + hashlib.sha1(public_key_string).hexdigest()
        public_wallet = (address, public_key)
        if public_wallet not in self._public_wallets:
            self._public_wallets.append(public_wallet)

    def store_block(self, block):
        '''
        Store a new block in this node.
        '''
        if block not in self._blocks:
            self._blocks.append(block)

    def store_node(self, node):
        '''
        Register a new peer.
        '''
        if node not in self._peers:
            self._peers.append(node)

    @staticmethod
    def create_wallet(seed=None):
        '''
        Generate a new wallet. The wallet uses a key pair and an address
        based on the SHA1 of the generated wallet's public key. The keys
        generated use the ECDSA key generation algorithm with the curve
        SECP256k1, the same as bitcoin.
        '''
        from ecdsa import SigningKey, SECP256k1
        from ecdsa.util import randrange_from_seed__trytryagain
        logging.debug("Creating wallet(seed={})".format(seed))
        if seed is None:
            seed = ''.join([random.SystemRandom().
                            choice(string.ascii_letters + string.digits)
                            for _ in range(50)])
        seed = int(hashlib.sha256(seed).hexdigest(), 16)
        secret_exponent = randrange_from_seed__trytryagain(seed,
                                                           SECP256k1.order)
        private_key = SigningKey.from_secret_exponent(secret_exponent,
                                                      curve=SECP256k1)
        public_key = private_key.get_verifying_key()
        address = 'QC' + hashlib.sha1(public_key.to_string()).hexdigest()
        wallet = {
            'private_key': binascii.b2a_base64(private_key.to_string()),
            'public_key': binascii.b2a_base64(public_key.to_string()),
            'address': address
        }
        return wallet

    def ammount_owned(self, wallet):
        '''
        Calculates the ammount owned by a wallet. This function is O(n^3) so
        call this with caution.
        '''
        ammount_owned = 0.0
        for block in self.blocks():
            for transaction in block.transactions():
                if wallet == transaction.from_wallet():
                    ammount_owned = ammount_owned - transaction.ammount_spent()
                else:
                    for transaction_wallet, ammount in \
                            transaction.to_wallets():
                        # There are no restriction as to what one can send
                        # money to a wallet in different ammounts all in the
                        # same transaction
                        if transaction_wallet == wallet:
                            ammount_owned = ammount_owned + ammount

        return ammount_owned
