import sys
from typing import Optional, Any, List
from google.oauth2 import service_account
from google.cloud import secretmanager
from google.auth import compute_engine, exceptions as gaexceptions
from google.api_core import exceptions as gexceptions
from libs import log, settings
from os import path

logger = log.fullon_logger(__name__)

SECRETS = ['DBPASSWD', 'APIFY_TOKEN']


class SecretManager:
    """
    Google secret manager
    """
    _project: str = None
    credentials: Optional[service_account.Credentials] = None
    secrets: Optional[secretmanager.SecretManagerServiceClient] = None
    client: Optional[secretmanager.SecretManagerServiceClient] = None

    def __init__(self):
        """
        constructor
        """
        paths = ["/etc/fullon/fullon_hush.json", "conf/fullon_hush.json", "fullon/conf/fullon_hush.json"]
        self.credentials = self._get_credentials(paths)
        if not self.credentials:
            msg = "Need a good google.json file with rights access to secret "
            msg += "Google keys in /etc/fullon/fullon_hush.json or "
            msg += "conf/fullon_hush.json or fullon/conf/fullon_hush.json"
            logger.error(msg)
            raise FileNotFoundError("No google secret file found")
        project = settings.SECRETPROJECT
        if not self._test_credentials(project=project):
            logger.info("Can't load google secret manager exiting")
            sys.exit()
        self._project = project
        # Create the Secret Manager client.
        logger.info("SecretManager authenticated, project: %s", project)

    def _get_credentials(self, paths: List[str]) -> Optional[service_account.Credentials]:
        """
        Retrieve credentials from given paths.

        Args:
            paths (List[str]): List of paths to check for the credentials file.

        Returns:
            service_account.Credentials: The loaded credentials.

        Raises:
            FileNotFoundError: If no credential file is found in any of the paths.
        """
        for path_str in paths:
            if path.exists(path_str):
                return service_account.Credentials.from_service_account_file(path_str)
        return None

    def _test_credentials(self, project: str) -> bool:
        """
        Tests if the Google Cloud credentials are working.   
        Args:
        - project (str): The project to check for authentication.

        Returns:
        - bool: A boolean indicating if the credentials are valid.
        """
        self.client = secretmanager.SecretManagerServiceClient(credentials=self.credentials)
        parent = f"projects/{project}"
        secrets = False
        try:
            secrets = self.client.list_secrets(request={"parent": parent})
        except gexceptions.ServiceUnavailable:
            pass
        except gaexceptions.TransportError:
            pass
        except gexceptions.PermissionDenied:
            mesg = (f"You don't have access to the project ({project}) with current "
                    "credentials. Edit this file and change project variable.")
            logger.info(mesg)
            sys.exit()
        if secrets:
            self.secrets = secrets
            return True
        return False

    def create_secret(self, secret_id: str) -> None:
        """
        Create a new secret with the given name. A secret is a logical wrapper
        around a collection of secret versions. Secret versions hold the actual
        secret material.  It creates the variable on googles server.

        Args:
        -  secret_id (str): The project to check for authentication.

        Returns:
        - None
        """
        # Build the resource name of the parent project.
        parent = f"projects/{self._project}"
        # Create the secret.
        response = self.client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        # Print the new secret name.
        mesg = f"Created secret: {secret_id}".format(response.name)
        logger.info(mesg)

    def add_secret_version(self, secret_id: str, payload: Any) -> bool:
        """
        Adds a new version to an existing secret.
        Args:
        - secret_id (str): The ID of the secret to add a new version to.
        - payload (str): The payload of the secret.

        Returns:
            bool: True or False on success
        """
        parent = f"projects/{self._project}/secrets/{secret_id}"
        payload = payload.encode('UTF-8')
        try:
            response = self.client.add_secret_version(parent=parent, payload={'data': payload})
        except gexceptions.NotFound:
            self.create_secret(secret_id=secret_id)
            response = self.client.add_secret_version(parent=parent, payload={'data': payload})
        if response:
            logger.info("Added secret version: %s", response.name)
            return True
        return False

    def access_secret_version(self, secret_id: str, version_id: str = "latest") -> Optional[str]:
        """
        Reads the content of a secret with a given ID and version. Returns the secret's payload as a string.

        Args:
            secret_id (str): The ID of the secret to access.
            version_id (str, optional): The version of the secret to access. Defaults to "latest".

        Returns:
            str: The secret's payload as a string if successful, otherwise None.

        """
        # Build the resource name of the secret version.
        secret_id = str(secret_id)
        name = f"projects/{self._project}/secrets/{secret_id}/versions/{version_id}"
        # Access the secret version.
        try:
            response = self.client.access_secret_version(name=name)
            return response.payload.data.decode('UTF-8')
        except gexceptions.Unauthenticated:
            logger.info("Bad credentials")
        except gexceptions.PermissionDenied:
            logger.info("Current account does not have permissions")
        except gexceptions.NotFound:
            logger.info("Key (%s.%s) not found", self._project, secret_id)
        return ""

    def delete_old_versions(self, uid):
        try:
            # List all secret versions
            parent = f"projects/{settings.SECRETPROJECT}/secrets/{uid}"
            response = self.client.list_secret_versions(request={"parent": parent})
            secret_versions = list(response)
            # Delete all secret versions except the last one
            for version in secret_versions[:-1]:
                try:
                    self.client.delete_secret_version(request={"name": version.name})
                    print(f"Deleted secret version: {version.name}")
                    return True
                except gexceptions.NotFound:
                    print(f"Secret version {version.name} not found")
        except gexceptions.NotFound:
            print(f"Secret {uid} not found")
        return False

    def delete_secret(self, secret_id: str) -> None:
        """
        Deletes the secret with a given ID.

        Args:
            secret_id (str): The ID of the secret to delete.

        Returns:
            None.

        """
        try:
            secret_id = f"projects/{self._project}/secrets/{secret_id}"
            self.client.delete_secret(name=secret_id)
        except gexceptions.Unauthenticated:
            logger.info("Bad credentials")
        except gexceptions.PermissionDenied:
            logger.info("Current account does not have permissions")
        except gexceptions.NotFound:
            logger.info("Key (%s.%s) not found", self._project, secret_id)

    def create_fullon_default_secrets(self) -> None:
        """ creates default fullon secrets """
        for secret in SECRETS:
            self.add_secret_version(secret_id=secret, payload="default")
