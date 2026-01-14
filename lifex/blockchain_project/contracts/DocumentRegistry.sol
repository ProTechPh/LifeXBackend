// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title DocumentRegistry
 * @dev Smart contract for storing document hashes on blockchain
 * 
 * BLOCKCHAIN BASICS:
 * - This contract runs on the Ethereum blockchain (Ganache in our case)
 * - Once data is written, it CANNOT be changed or deleted (immutable)
 * - Every transaction costs "gas" (fake ETH on Ganache)
 * - Anyone can read data, but only authorized users can write
 */

contract DocumentRegistry {
    
    // STRUCT: A custom data type (like a class in Python)
    struct Document {
        string documentHash;      // SHA-256 hash of the document
        address owner;            // Ethereum address of document owner
        uint256 timestamp;        // When document was registered
        string documentType;      // Type of document (e.g., "KYC_ID", "KYC_ADDRESS")
        bool exists;              // Flag to check if document exists
    }
    
    // MAPPING: Like a Python dictionary {key: value}
    // Maps: user_address => (document_id => Document)
    mapping(address => mapping(string => Document)) private documents;
    
    // Array to store all document IDs for a user
    mapping(address => string[]) private userDocumentIds;
    
    // EVENT: Broadcasts when something happens (like signals in Django)
    event DocumentRegistered(
        address indexed owner,
        string documentId,
        string documentHash,
        string documentType,
        uint256 timestamp
    );
    
    event DocumentVerified(
        address indexed owner,
        string documentId,
        bool isValid,
        uint256 timestamp
    );
    
    /**
     * @dev Register a new document hash
     * @param _documentId Unique identifier for the document
     * @param _documentHash SHA-256 hash of the document
     * @param _documentType Type of document being registered
     */
    function registerDocument(
        string memory _documentId,
        string memory _documentHash,
        string memory _documentType
    ) public returns (bool) {
        
        // Check if document already exists
        require(
            !documents[msg.sender][_documentId].exists,
            "Document already registered"
        );
        
        // Create new document record
        documents[msg.sender][_documentId] = Document({
            documentHash: _documentHash,
            owner: msg.sender,
            timestamp: block.timestamp,
            documentType: _documentType,
            exists: true
        });
        
        // Add to user's document list
        userDocumentIds[msg.sender].push(_documentId);
        
        // Emit event (this can be listened to by Django)
        emit DocumentRegistered(
            msg.sender,
            _documentId,
            _documentHash,
            _documentType,
            block.timestamp
        );
        
        return true;
    }
    
    /**
     * @dev Verify if a document hash matches what's stored
     * @param _documentId Document identifier
     * @param _documentHash Hash to verify
     */
    function verifyDocument(
        string memory _documentId,
        string memory _documentHash
    ) public returns (bool) {
        
        // Check if document exists
        require(
            documents[msg.sender][_documentId].exists,
            "Document not found"
        );
        
        // Compare stored hash with provided hash
        bool isValid = keccak256(
            abi.encodePacked(documents[msg.sender][_documentId].documentHash)
        ) == keccak256(abi.encodePacked(_documentHash));
        
        // Emit verification event
        emit DocumentVerified(
            msg.sender,
            _documentId,
            isValid,
            block.timestamp
        );
        
        return isValid;
    }
    
    /**
     * @dev Get document details
     * @param _owner Address of document owner
     * @param _documentId Document identifier
     */
    function getDocument(
        address _owner,
        string memory _documentId
    ) public view returns (
        string memory documentHash,
        address owner,
        uint256 timestamp,
        string memory documentType,
        bool exists
    ) {
        Document memory doc = documents[_owner][_documentId];
        return (
            doc.documentHash,
            doc.owner,
            doc.timestamp,
            doc.documentType,
            doc.exists
        );
    }
    
    /**
     * @dev Get all document IDs for a user
     * @param _owner Address of document owner
     */
    function getUserDocuments(
        address _owner
    ) public view returns (string[] memory) {
        return userDocumentIds[_owner];
    }
    
    /**
     * @dev Get total number of documents for a user
     * @param _owner Address of document owner
     */
    function getDocumentCount(
        address _owner
    ) public view returns (uint256) {
        return userDocumentIds[_owner].length;
    }
}