// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title NicheBetEscrow
 * @notice EVM Escrow contract holding USDC deposits for P2P Prediction Markets.
 * Disburses 100% of the pool to the winning bettor upon GenLayer settlement relay signal.
 */
contract NicheBetEscrow {
    address public owner;
    address public settlementRelay;

    struct MarketEscrow {
        bytes32 marketId;
        address bettorYes;
        address bettorNo;
        uint256 stakeAmount;
        bool isSettled;
        address winner;
    }

    mapping(bytes32 => MarketEscrow) public markets;

    event MarketFunded(bytes32 indexed marketId, address indexed bettorYes, address indexed bettorNo, uint256 totalPool);
    event WinningsDisbursed(bytes32 indexed marketId, address indexed winner, uint256 payoutAmount);
    event MarketRefunded(bytes32 indexed marketId, uint256 refundPerBettor);

    modifier onlyRelay() {
        require(msg.sender == settlementRelay || msg.sender == owner, "Only authorized relay or owner");
        _;
    }

    constructor(address _settlementRelay) {
        owner = msg.sender;
        settlementRelay = _settlementRelay;
    }

    function setSettlementRelay(address _newRelay) external {
        require(msg.sender == owner, "Only owner");
        settlementRelay = _newRelay;
    }

    function createEscrow(bytes32 marketId, address bettorYes, address bettorNo, uint256 stakeAmount) external payable {
        require(markets[marketId].stakeAmount == 0, "Market escrow already exists");
        require(bettorYes != address(0) && bettorNo != address(0), "Invalid bettor addresses");

        markets[marketId] = MarketEscrow({
            marketId: marketId,
            bettorYes: bettorYes,
            bettorNo: bettorNo,
            stakeAmount: stakeAmount,
            isSettled: false,
            winner: address(0)
        });

        emit MarketFunded(marketId, bettorYes, bettorNo, stakeAmount * 2);
    }

    function disburseWinnings(bytes32 marketId, address winner) external onlyRelay {
        MarketEscrow storage m = markets[marketId];
        require(!m.isSettled, "Market already settled");
        require(winner == m.bettorYes || winner == m.bettorNo, "Invalid winner address");

        m.isSettled = true;
        m.winner = winner;

        uint256 totalPayout = m.stakeAmount * 2;
        payable(winner).transfer(totalPayout);

        emit WinningsDisbursed(marketId, winner, totalPayout);
    }

    function refundAll(bytes32 marketId) external onlyRelay {
        MarketEscrow storage m = markets[marketId];
        require(!m.isSettled, "Market already settled");

        m.isSettled = true;

        if (m.bettorYes != address(0)) {
            payable(m.bettorYes).transfer(m.stakeAmount);
        }
        if (m.bettorNo != address(0)) {
            payable(m.bettorNo).transfer(m.stakeAmount);
        }

        emit MarketRefunded(marketId, m.stakeAmount);
    }

    receive() external payable {}
}
