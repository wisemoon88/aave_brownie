from operator import ge
from brownie import network, config, interface
from scripts.helpful_scripts import get_account
from scripts.get_weth import get_weth
from web3 import Web3

amount = Web3.toWei(0.1, "ether")


def main():
    account = get_account()
    erc20_address = config["networks"][network.show_active()]["weth_token"]
    if network.show_active() in ["mainnet-fork"]:
        get_weth()
    # get_weth()
    lending_pool = get_lending_pool()
    print(lending_pool)
    # this approves the erc20 token to be used by the lending pool address by a certain amount, approved via account
    approve_erc20(amount, lending_pool.address, erc20_address, account)
    print("depositing weth")
    tx = lending_pool.deposit(
        erc20_address, amount, account.address, 0, {"from": account}
    )
    tx.wait(1)
    print("deposited")
    borrowable_eth, total_debt = get_borrowable_data(lending_pool, account)
    print("lets start borrowing!!")
    # before borrownig DAI will need to find conversion rate of eth to dai
    dai_eth_price = get_asset_price(
        config["networks"][network.show_active()]["dai_eth_price_feed"]
    )
    # amount of dai we are able to borrow based on our borrowable eth with a buffer
    amount_dai_to_borrow = (1 / dai_eth_price) * (borrowable_eth * 0.95)
    print(f"we are going to borrow {amount_dai_to_borrow} dai")
    dai_addresss = config["networks"][network.show_active()]["dai_token"]
    borrow_tx = lending_pool.borrow(
        dai_addresss,
        Web3.toWei(amount_dai_to_borrow, "ether"),
        1,
        0,
        account.address,
        {"from": account},
    )
    borrow_tx.wait(1)
    print("borrowed DAI from ETH")
    get_borrowable_data(lending_pool, account)
    repay_all(amount, lending_pool, account)
    print("you just deposited, borrowed, and repayed usng brownie!")


def repay_all(amount, lending_pool, account):
    approve_erc20(
        Web3.toWei(amount, "ether"),
        lending_pool,
        config["networks"][network.show_active()]["dai_token"],
        account,
    )
    repay_tx = lending_pool.repay(
        config["networks"][network.show_active()]["dai_token"],
        amount,
        1,
        account.address,
        {"from": account},
    )
    repay_tx.wait(1)
    print("repayed!!")


def get_asset_price(price_feed_address):
    dai_eth_price_feed = interface.AggregatorV3Interface(price_feed_address)
    latest_price = dai_eth_price_feed.latestRoundData()[1]
    converted_latest_price = Web3.fromWei(latest_price, "ether")
    print(f"latest DAI/ETHprice is {converted_latest_price}")
    return float(converted_latest_price)


def get_borrowable_data(lending_pool, account):
    (
        total_collateral_eth,
        total_debt_eth,
        available_borrow_eth,
        current_liquidation_threshold,
        ltv,
        health_factor,
    ) = lending_pool.getUserAccountData(account.address)
    available_borrow_eth = Web3.fromWei(available_borrow_eth, "ether")
    total_collateral_eth = Web3.fromWei(total_collateral_eth, "ether")
    total_debt_eth = Web3.fromWei(total_debt_eth, "ether")
    print(f"you have {available_borrow_eth} worth of eth able to be borrowed")
    print(f"you have {total_collateral_eth} worth of eth deposited")
    print(f"you have {total_debt_eth} worth of eth borrowed")
    return (float(available_borrow_eth), float(total_debt_eth))


def get_lending_pool():
    lending_pool_addresses_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )
    # getting the current address of the lending pool contract
    lending_pool_address = lending_pool_addresses_provider.getLendingPool()

    # calling the lending pool contract
    lending_pool = interface.ILendingPool(lending_pool_address)
    return lending_pool


# before depositnig wrapped ether need to approve the address sending out first


def approve_erc20(amount, spender, erc20_address, account):
    print("approving erc20 token..")
    erc20 = interface.IERC20(erc20_address)
    tx = erc20.approve(spender, amount, {"from": account})
    tx.wait(1)
    print("approved!!")
    return tx
