"""Local coursework server with supplied public Sepolia manifest; no deployment."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app
root=Path(__file__).resolve().parent.parent
manifest_path=root/'deployment/sepolia.json'
manifest=json.loads(manifest_path.read_text())
app=create_app({
    'DATABASE': os.getenv('DATABASE_PATH') or str(root/'local-sepolia.db'),
    'BLOCKCHAIN_CHAIN_ID': manifest['chainId'],
    'BLOCKCHAIN_DEPLOYMENT_ID': manifest['deploymentId'],
    'BLOCKCHAIN_MANIFEST_PATH': str(manifest_path),
    'ROLE_REGISTRY_ADDRESS': manifest['contracts']['RoleRegistry']['address'],
    'FUNDING_CONTRACT_ADDRESS': manifest['contracts']['deposit_money']['address'],
    'REMITTANCE_CONTRACT_ADDRESS': manifest['contracts']['paynow']['address'],
})
if __name__=='__main__':
    app.run(host='127.0.0.1',port=5000,debug=False)
