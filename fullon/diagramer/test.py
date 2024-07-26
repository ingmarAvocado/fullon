from graphviz import Digraph

def create_system_architecture():
    dot = Digraph(comment='System Architecture')
    dot.attr(rankdir='LR')

    # Add nodes
    dot.node('ClientSystem', "Client's Existing\nLoyalty System")
    dot.node('API', 'API Layer')
    dot.node('SaaSSystem', 'Your SaaS Web3\nLoyalty Program')
    dot.node('WalletService', 'Web3 Wallet\nCreation Service')
    dot.node('Blockchain', 'Blockchain')

    # Add edges
    dot.edge('ClientSystem', 'API', 'Interacts with')
    dot.edge('API', 'SaaSSystem', 'Manages')
    dot.edge('SaaSSystem', 'WalletService', 'Creates wallets')
    dot.edge('WalletService', 'Blockchain', 'Interacts with')

    dot.render('system_architecture', view=True, format='png')

def create_user_registration_flow():
    dot = Digraph(comment='User Registration Flow')
    dot.attr(rankdir='LR')

    # Add nodes
    dot.node('Client', "Client's System")
    dot.node('API', 'Your API')
    dot.node('Wallet', 'Web3 Wallet Service')
    dot.node('DB', 'Your Database', shape='cylinder')

    # Add edges
    dot.edge('Client', 'API', 'Send external user_id')
    dot.edge('API', 'Wallet', 'Request wallet creation')
    dot.edge('Wallet', 'API', 'Return wallet address')
    dot.edge('API', 'DB', 'Associate user_id with wallet')
    dot.edge('API', 'Client', 'Confirm registration')

    dot.render('user_registration_flow', view=True, format='png')

def create_user_interaction_flow():
    dot = Digraph(comment='User Interaction Flow')
    dot.attr(rankdir='LR')

    # Add nodes
    dot.node('User', 'User')
    dot.node('Client', "Client's System")
    dot.node('API', 'Your API')
    dot.node('SaaS', 'Your SaaS System')

    # Add edges
    dot.edge('User', 'Client', 'Log in')
    dot.edge('Client', 'API', 'Request token login')
    dot.edge('API', 'Client', 'Return authentication token')
    dot.edge('Client', 'API', 'Request campaign data')
    dot.edge('API', 'SaaS', 'Fetch campaign data')
    dot.edge('SaaS', 'API', 'Return campaign data')
    dot.edge('API', 'Client', 'Return campaign data')
    dot.edge('Client', 'User', 'Display authenticated webview (iframe)')

    dot.render('user_interaction_flow', view=True, format='png')

if __name__ == "__main__":
    create_system_architecture()
    create_user_registration_flow()
    create_user_interaction_flow()
