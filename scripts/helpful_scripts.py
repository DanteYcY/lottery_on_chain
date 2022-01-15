"""
It's a good habit to list all frequent used functions independenly in a py
so that we can call and use them everytime we need
"""
from brownie import (
    network,
    config,
    accounts,
    MockV3Aggregator,
    Contract,
    VRFCoordinatorMock,
    LinkToken,
    interface,
    chain,
)
import requests
import time
import web3

# This part is used to preset frequent used variables
LOCAL_BLOCKCHAIN_ENVIRONMENT = ["development", "ganache-local"]
FORKED_LOCAL_ENVIRONMENTS = ["mainnet-fork", "mainnet-fork-dev"]
DECIMALS = 8
STARTING_PRICE = 200000000000

# This function is used to get account information
def get_account(index=None, id=None):
    if index:
        return accounts[index]
    if id:
        return accounts.load(id)
    # if the current ran network is a local development network or a fork network, return the address directly
    if (
        network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENT
        or network.show_active() in FORKED_LOCAL_ENVIRONMENTS
    ):
        return accounts[0]
    # if it's on mainnet or a testnet, get the information from environment variables
    else:
        return accounts.add(config["wallets"]["from_key"])


# If it's in development environment, we deploy contracts using MockV3Aggregator to get Eth price
def deploy_mocks():
    account = get_account()
    print(f"The active network is {network.show_active()}")
    print("Deploying Mocks...")
    # if we haven't deployed the mock contract yet,
    if len(MockV3Aggregator) <= 0:
        # deploy it with preset parameters to the chain
        MockV3Aggregator.deploy(DECIMALS, STARTING_PRICE, {"from": account})
    if len(LinkToken) <= 0:
        link_token = LinkToken.deploy({"from": account})
    if len(VRFCoordinatorMock) <= 0:
        VRFCoordinatorMock.deploy(link_token.address, {"from": account})
    print("Mocks Deployed!")


contract_to_mock = {
    "eth_usd_price_feed": MockV3Aggregator,
    "vrf_coordinator": VRFCoordinatorMock,
    "link_token": LinkToken,
}


def get_contract(contract_name):
    """
    This function will grab the contract address from the brownie config if defined,
    otherwise, it will deploy a mock version of that contract,
    and return that mock contract

        Args:
            contract_name (string)

        Returns:
            brownie.network.contract.ProjectContract: The most recently deployed
            version of this contract.

    """
    contract_type = contract_to_mock[contract_name]
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENT:
        if len(contract_type) <= 0:
            deploy_mocks()
        contract = contract_type[-1]
    else:
        contract_address = config["networks"][network.show_active()][contract_name]
        contract = Contract.from_abi(
            contract_type._name, contract_address, contract_type.abi
        )
    return contract


def fund_with_link(
    contract_address, _account=None, _link_token=None, amount=100000000000000000
):
    account = _account if _account else get_account()
    link_token = _link_token if _link_token else get_contract("link_token")
    tx = link_token.transfer(contract_address, amount, {"from": account})
    # link_token_contract = interface.LinkTokenInterface(link_token.address)
    # tx = link_token_contract.transfer(contract_address, amount, {"from": account})
    tx.wait(1)
    print("Fund LinkToken contract!")
    return tx


def wait_for_randomness(lottery):
    # Keeps checking for a fulfillRandomness callback using the block explorer's API, and returns the randomness

    # Initial frequency, in seconds
    sleep_time = 120
    # Last checked block num
    from_block = len(chain)
    print("Waiting For Data...\n")
    i = 1

    # Until randomness received
    while True:
        print(f"Check #{i} in {sleep_time} secs\n")
        # Wait
        time.sleep(sleep_time)
        # Get last mined block num
        to_block = len(chain)

        # Check if randomness received
        # 🔗 See https://docs.etherscan.io/api-endpoints/logs
        response = requests.get(
            config["networks"][network.show_active()]["explorer_api"],
            params={
                "module": "logs",
                "action": "getLogs",
                "fromBlock": from_block,
                "toBlock": to_block,
                "address": lottery.address,
                "topic0": web3.Web3.keccak(text="RandomnessReceived(uint256)").hex(),
                "apikey": config["api_keys"]["etherscan"],
            },
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36"
            },
        ).json()
        # Return randomness if received
        if response["status"] == "1":
            return int(response["result"][0]["data"], 16)

        # Half sleep time if longer than 15 seconds
        if sleep_time > 15:
            sleep_time = int(round(sleep_time / 2))

        from_block = to_block

        i += 1
