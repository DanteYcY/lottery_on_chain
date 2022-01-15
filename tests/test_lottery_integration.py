# less than 0.01 ETH
from brownie import Lottery, accounts, config, network, exceptions
from scripts.deploy_lottery import deploy_lottery
import pytest
from scripts.helpful_scripts import (
    LOCAL_BLOCKCHAIN_ENVIRONMENT,
    get_account,
    fund_with_link,
    wait_for_randomness,
)
import time


def test_integration  ():
    # Arrange
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENT:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    link_transaction = fund_with_link(lottery.address)
    transaction = lottery.endLottery({"from": account})
    randomness = wait_for_randomness(lottery)
    assert lottery.recentWinner() == account
    assert lottery.balance() == 0

