// This file tells Truffle how to deploy our smart contract to Ganache

const DocumentRegistry = artifacts.require("DocumentRegistry");

module.exports = function (deployer) {
  // Deploy the DocumentRegistry contract
  deployer.deploy(DocumentRegistry);
};

// HOW TO USE THIS FILE:
// 1. Save DocumentRegistry.sol in blockchain_project/contracts/
// 2. Save this file in blockchain_project/migrations/
// 3. Make sure Ganache is running
// 4. Run: truffle migrate --reset
// 5. Copy the contract address from the output
// 6. Update Django settings with the contract address