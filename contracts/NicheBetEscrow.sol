// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title NicheBetEscrow
 * @notice Production Native-Currency P2P Prediction Market Escrow Contract.
 * @dev Enforces full 2-sided collateral funding, participant binding to GenLayer market records,
 * and autonomous disbursement/refund upon authenticated GenLayer settlement relay signal.
 */
contract NicheBetEscrow {
    address public owner;
    address public settlementRelay;

    struct MarketEscrow {
        bytes32 marketId;
        address bettorYes;
        address bettorNo;
        uint256 stakeAmount;
        bool yesFunded;
        bool noFunded;
        bool isFunded;
        bool isSettled;
        address winner;
    }

    mapping(bytes32 => MarketEscrow) public markets;

    event MarketCreated(bytes32 indexed marketId, address indexed bettorYes, address indexed bettorNo, uint256 stakeAmount);
    event BetFunded(bytes32 indexed marketId, address indexed bettor, uint8 side, uint256 amount);
    event EscrowFullyFunded(bytes32 indexed marketId, uint256 totalPool);
    event WinningsDisbursed(bytes32 indexed marketId, address indexed winner, uint256 payoutAmount);
    event MarketRefunded(bytes32 indexed marketId, uint256 refundPerBettor);

    modifier onlyRelay() {
        require(msg.sender == settlementRelay || msg.sender == owner, "Only authorized settlement relay or owner");
        _;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor(address _settlementRelay) {
        owner = msg.sender;
        settlementRelay = _settlementRelay;
    }

    function setSettlementRelay(address _newRelay) external onlyOwner {
        require(_newRelay != address(0), "Invalid relay address");
        settlementRelay = _newRelay;
    }

    /**
     * @notice Creates a new market escrow bound to GenLayer participant addresses.
     */
    function createMarket(bytes32 marketId, address bettorYes, address bettorNo, uint256 stakeAmount) external {
        require(markets[marketId].stakeAmount == 0, "Market escrow already registered");
        require(bettorYes != address(0) && bettorNo != address(0), "Invalid bettor addresses");
        require(bettorYes != bettorNo, "Self-matching prohibited: opposing bettors required");
        require(stakeAmount > 0, "Stake amount must be > 0");

        markets[marketId] = MarketEscrow({
            marketId: marketId,
            bettorYes: bettorYes,
            bettorNo: bettorNo,
            stakeAmount: stakeAmount,
            yesFunded: false,
            noFunded: false,
            isFunded: false,
            isSettled: false,
            winner: address(0)
        });

        emit MarketCreated(marketId, bettorYes, bettorNo, stakeAmount);
    }

    /**
     * @notice Funds a specific side (YES=1, NO=2) with exact native currency collateral.
     */
    function fundBet(bytes32 marketId, uint8 side) external payable {
        MarketEscrow storage m = markets[marketId];
        require(m.stakeAmount > 0, "Market escrow does not exist");
        require(!m.isSettled, "Market already settled");
        require(msg.value == m.stakeAmount, "Exact native stake amount required");

        if (side == 1) { // YES
            require(msg.sender == m.bettorYes, "Sender must match registered YES bettor");
            require(!m.yesFunded, "YES side already funded");
            m.yesFunded = true;
            emit BetFunded(marketId, msg.sender, 1, msg.value);
        } else if (side == 2) { // NO
            require(msg.sender == m.bettorNo, "Sender must match registered NO bettor");
            require(!m.noFunded, "NO side already funded");
            m.noFunded = true;
            emit BetFunded(marketId, msg.sender, 2, msg.value);
        } else {
            revert("Invalid side: 1=YES, 2=NO");
        }

        if (m.yesFunded && m.noFunded) {
            m.isFunded = true;
            emit EscrowFullyFunded(marketId, m.stakeAmount * 2);
        }
    }

    /**
     * @notice Convenience source-backed method to create and fully fund an escrow in 1 step.
     */
    function createAndFundEscrow(bytes32 marketId, address bettorYes, address bettorNo, uint256 stakeAmount) external payable {
        require(markets[marketId].stakeAmount == 0, "Market escrow already exists");
        require(bettorYes != address(0) && bettorNo != address(0), "Invalid bettor addresses");
        require(bettorYes != bettorNo, "Self-matching prohibited");
        require(stakeAmount > 0, "Stake amount must be > 0");
        require(msg.value == stakeAmount * 2, "Must supply 100% full pool funding (2 * stake)");

        markets[marketId] = MarketEscrow({
            marketId: marketId,
            bettorYes: bettorYes,
            bettorNo: bettorNo,
            stakeAmount: stakeAmount,
            yesFunded: true,
            noFunded: true,
            isFunded: true,
            isSettled: false,
            winner: address(0)
        });

        emit MarketCreated(marketId, bettorYes, bettorNo, stakeAmount);
        emit EscrowFullyFunded(marketId, stakeAmount * 2);
    }

    /**
     * @notice Disburses 100% of the collateral pool to the winning participant upon GenLayer verdict.
     */
    function disburseWinnings(bytes32 marketId, address winner) external onlyRelay {
        MarketEscrow storage m = markets[marketId];
        require(m.isFunded, "Escrow not fully funded");
        require(!m.isSettled, "Market already settled");
        require(winner == m.bettorYes || winner == m.bettorNo, "Winner must be registered market participant");

        m.isSettled = true;
        m.winner = winner;

        uint256 totalPayout = m.stakeAmount * 2;
        (bool sent, ) = payable(winner).call{value: totalPayout}("");
        require(sent, "Native transfer to winner failed");

        emit WinningsDisbursed(marketId, winner, totalPayout);
    }

    /**
     * @notice Refunds 100% of individual stakes if the GenLayer Court resolves VOID.
     */
    function refundAll(bytes32 marketId) external onlyRelay {
        MarketEscrow storage m = markets[marketId];
        require(m.isFunded, "Escrow not fully funded");
        require(!m.isSettled, "Market already settled");

        m.isSettled = true;
        uint256 refundAmount = m.stakeAmount;

        if (m.bettorYes != address(0)) {
            (bool sentYes, ) = payable(m.bettorYes).call{value: refundAmount}("");
            require(sentYes, "Refund to YES bettor failed");
        }
        if (m.bettorNo != address(0)) {
            (bool sentNo, ) = payable(m.bettorNo).call{value: refundAmount}("");
            require(sentNo, "Refund to NO bettor failed");
        }

        emit MarketRefunded(marketId, refundAmount);
    }

    receive() external payable {}
}
