// SPDX-Lisence-Identifier: MIT

pragma solidity ^0.6.6;

// Import AggregatorV3Interface to get latest price
import "@chainlink/contracts/src/v0.6/interfaces/AggregatorV3Interface.sol";
// Import VRFConsumerBase to get random number with Chainlink
import "@chainlink/contracts/src/v0.6/VRFConsumerBase.sol";

// Lottery contract will inherit all the function from VRFConsumerBase
contract Lottery is VRFConsumerBase {
    // players is a public array of payable address
    address payable[] public players;
    uint256 public usdEntryFee;
    // ethUSDPriceFeed is the imported interface type
    AggregatorV3Interface public ethUSDPriceFeed;
    // enum restricts a variable to have one of only a few predefined values
    // Here we define LOTTERY_STATE is enum type of variables that has three predefined values
    // 0 = OPEN, 1 = CLOSED, 2 = CALCULATING_WINNER
    enum LOTTERY_STATE {
        OPEN,
        CLOSED,
        CALCULATING_WINNER
    }
    // lottery_state is LOTTERY_STATE type variable
    LOTTERY_STATE public lottery_state;
    // We use these two variables as input to get random number
    bytes32 public keyHash;
    uint256 public fee;
    // this variable has to be a payable address because the lottery will transfer all the balance to it
    address payable public recentWinner;
    uint256 public randomness;
    address public owner;
    event RequestedRandomness(bytes32 requestId);
    event RandomnessReceived(uint256 _randomness);

    constructor(
        // 5 inputs are needed to initialize the contract
        // some inputs are needed by our defined functions
        // other inputs are needed by the functions from the inherited contract
        address _priceFeedAddress,
        address _vrfCoordinator,
        address _link,
        uint256 _fee,
        bytes32 _keyHash
    )
        public
        // we can assign the needed inputs to initialize the inherited contract here
        VRFConsumerBase(_vrfCoordinator, _link)
    {
        // the outputs are usually some variables needed by some functions
        // the outputs of the constructor are those we don't want other operators to change
        usdEntryFee = 50 * (10**18);
        ethUSDPriceFeed = AggregatorV3Interface(_priceFeedAddress);
        lottery_state = LOTTERY_STATE.CLOSED;
        // these two are needed to use the function within that inherited contract
        fee = _fee;
        keyHash = _keyHash;
        // we defined owner as the constructor
        owner = msg.sender;
    }

    function enter() public payable {
        // $50 minimum
        // other players (operators) can only send ETH to the contract when the state is open
        require(lottery_state == LOTTERY_STATE.OPEN);
        // the sended ETH must exceed the entrance level, otherwise the message will return
        require(msg.value >= getEntranceFee(), "Please send more ETH!");
        // if the players send ETH successfuly, its address will be added to the array
        // the list will be used for lottery later
        players.push(msg.sender);
    }

    function getEntranceFee() public view returns (uint256) {
        // AggregatorV3Interface get the latest price.
        (, int256 answer, , , ) = ethUSDPriceFeed.latestRoundData();
        // because latestRoundData returns a price with unit of Gwei
        // we transfer it to wei here
        uint256 adjustedPrice = uint256(answer) * 10**10;
        // usdEntranceFee is 50 * 10**18, adjustedPrice also has 10**18.
        // so the costToEnter is a number with 10**18, which means its unit is wei
        uint256 costToEnter = (usdEntryFee * 10**18) / adjustedPrice;
        return costToEnter;
    }

    // use onlyOwner modifier to restrict the startLottery function, only constructor can start
    function startLottery() public onlyOwner {
        require(lottery_state == LOTTERY_STATE.CLOSED);
        // start the lottery by changing its state from closed to open
        lottery_state = LOTTERY_STATE.OPEN;
    }

    // only constructor can end the lottery process
    function endLottery() public onlyOwner {
        require(lottery_state == LOTTERY_STATE.OPEN);
        // change the state from open to calculating_winner
        lottery_state = LOTTERY_STATE.CALCULATING_WINNER;
        // requestRandomness function is inherited from VRFConsumerBase
        // remember we input _vrfCoordinator, _link to start the whole contract
        // those two are needed in VRFConsumerBase's constructor
        // but keyHash and fee are inputs of this specific function
        // it returns a bytes32 variable as a Id to call the result later
        bytes32 requestId = requestRandomness(keyHash, fee);
        emit RequestedRandomness(requestId);
    }

    // fulfillRandomness is an internal function, means it's not visible or operatable by any player
    // this fulfillRandomness will override the virtual function defined in the inherited concract
    // this function doesn't specify the operator, anyone can operate this function to see the result of the lottery
    // but people cannot use any random number they want
    // because the random number will be validated with this requestId on the blockchain
    function fulfillRandomness(bytes32 _requestId, uint256 _randomness)
        internal
        override
    {
        // This function can only be operated during calculating_winner
        require(
            lottery_state == LOTTERY_STATE.CALCULATING_WINNER,
            "You aren't there yet!"
        );
        require(_randomness > 0, "random-not-found");
        // get the reminder of randomness/player number
        uint256 indexOfWinner = _randomness % players.length;
        // use the reminder as index to get the address of the winner
        recentWinner = players[indexOfWinner];
        // transfer all the balance in the contract to that winner address
        recentWinner.transfer(address(this).balance);
        // reset everything to the beginning
        players = new address payable[](0);
        lottery_state = LOTTERY_STATE.CLOSED;
        // the random number can be checked by everyone
        randomness = _randomness;
        // Emit an event for testing purposes
        emit RandomnessReceived(_randomness);
    }

    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }
}
