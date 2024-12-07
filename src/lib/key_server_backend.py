"""
Key server backend

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import logging
import os

from sqlalchemy.exc import MultipleResultsFound
from phe import paillier

from src.lib import config
from src.lib.user import UserType
from src.lib.user_database import Producer, db, get_user
from src.key_server.key_database import (StoredKey, StoredTool, KeyRetrievalClient,
                                         KeyRetrievalProvider, IDRetrieval)


log: logging.Logger = logging.getLogger(__name__)


class KeyServer:
    """Key server of the platform"""

    def __init__(self, data_dir=config.DATA_DIR) -> None:
        """Set data directory and create it, if it does not exist."""
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(data_dir + '/logs/', exist_ok=True)

    @staticmethod
    def _gen_key(bit_length: int = config.KEY_LEN
                 ) -> tuple[paillier.PaillierPublicKey,
                            paillier.PaillierPrivateKey]:
        """
        Return a cryptographically random key pair with given length.

        :param bit_length: Length of keys [multiple of 1024]
        :return: Key pair with given bit length
        """
        if bit_length % 1024 != 0:
            raise ValueError("Bit length of keys should be multiple of 1024 bits.")
        return paillier.generate_paillier_keypair(n_length=bit_length)

    @staticmethod
    def _get_key(map_name: tuple[str, str, str]) -> StoredKey | None:
        """
        Return requested key to user.

        :param map_name: Map name (machine, material, tool)
        :return: Requested StoredKey
        """
        log.debug("Get map ID called.")
        machine, material, tool = map_name
        try:
            key = StoredKey.query.filter(
                StoredKey.machine == machine,
                StoredKey.material == material,
                StoredKey.tool.has(StoredTool.tool == tool)).one_or_none()
        except MultipleResultsFound as e:
            log.exception(str(e))
            raise ValueError from e
        return key

    @staticmethod
    def get_key_client_producer(map_name: tuple[str, str, str],
                                producer: str) -> tuple[int, int, int, int]:
        """
        Return map ID and private key for requested map to producer.
        Store access into database.

        :param map_name: Map name (machine, material, tool)
        :param producer: Username of producer requesting the key
        :return: Tuple of map ID, n value of public key,
            and p and q values of private key
            ]
        """
        log.debug("Get key client producer called.")
        client = get_user(UserType.Producer, producer)

        key = KeyServer._get_key(map_name)
        if not key:
            raise ValueError("Requested map not stored.")

        try:
            t = KeyRetrievalClient(producer=client,
                                   key=key)
            db.session.add(t)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError from e
        return (key.map_id, key.public_key_n,
                key.private_key_p, key.private_key_q)

    @staticmethod
    def get_key_provider(map_name: tuple[str, str, str],
                         tool_properties: tuple[str, int],
                         producer: str) -> tuple[int, int, int, int]:
        """
        Return ID and public key of requested map to producer.
        Store access into database.

        :param map_name: Map name (machine, material, tool)
        :param tool_properties: Tool properties (type, diameter)
        :param producer: Username of producer requesting the key
        :return: Tuple of map ID, n value of public key,
            and p and q values of private key
        """
        log.debug("Get key provider called.")
        provider = get_user(UserType.Producer, producer)
        machine, material, tool = map_name
        tool_type, tool_diameter = tool_properties

        key = KeyServer._get_key(map_name)
        if not key:
            log.debug("Requested map not stored, adding entry.")
            try:
                stored_tool = StoredTool.query.filter(
                    StoredTool.tool == tool,
                    StoredTool.tool_type == tool_type,
                    StoredTool.tool_diameter == tool_diameter).one_or_none()
            except MultipleResultsFound as e:
                log.exception(str(e))
                raise ValueError from e
            if not stored_tool:
                log.debug("Requested tool not stored, adding entry.")
                try:
                    stored_tool = StoredTool(tool=tool,
                                            tool_type=tool_type,
                                            tool_diameter=tool_diameter,
                                            first_provider=provider)
                    db.session.add(stored_tool)
                    db.session.commit() # necessary to set stored_tool.id
                except Exception as e:
                    db.session.rollback()
                    raise ValueError from e
            public_key, private_key = KeyServer._gen_key()
            try:
                key = StoredKey(machine=machine,
                                material=material,
                                tool=stored_tool,
                                public_key_n=public_key.n,
                                private_key_p=private_key.p,
                                private_key_q=private_key.q)
                db.session.add(key)
                db.session.commit() # necessary to set key.map_id
            except Exception as e:
                db.session.rollback()
                raise ValueError from e

        else:
            try:
                key = StoredKey.query.filter(
                    StoredKey.machine == machine,
                    StoredKey.material == material,
                    StoredKey.tool.has(StoredTool.tool == tool),
                    StoredKey.tool.has(StoredTool.tool_type == tool_type),
                    StoredKey.tool.has(StoredTool.tool_diameter == tool_diameter)).one()
            except ValueError as e:
                log.exception(str(e))
                raise ValueError("Different specifications stored for tool, "
                                 "please contact platform operators.") from e

        try:
            t = KeyRetrievalProvider(producer=provider,
                                     key=key)
            db.session.add(t)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError from e
        return (key.map_id, key.public_key_n,
                key.private_key_p, key.private_key_q)

    @staticmethod
    def get_map_ids(map_name_prefix: tuple[str, str],
                    tool_properties: tuple[str, int],
                    excluded_tools: list[str],
                    producer: str) -> tuple[list[int],
                                            list[tuple[int, int, int]]]:
        """
        Return ids and keys of maps relevant for reverse query to producer.
        Store access into database.

        :param map_name_prefix: Map name without tool (machine, material)
        :param tool_properties: Tool properties (type, diameter)
        :param excluded_tools: Tools not to retrieve map ID for
        :param producer: Username of producer requesting the tools
        :return: List of tuples of map ID, public key, and private key:
            [
                (map_id_1, public_key_n_1, private_key_p_1, private_key_q_1),
                (map_id_2, public_key_n_2, private_key_p_2, private_key_q_2),
                ...
            ]
        """
        log.debug("Get map ids called.")
        client = get_user(UserType.Producer, producer)
        machine, material = map_name_prefix
        tool_type, tool_diameter = tool_properties

        keys: list[StoredKey] = StoredKey.query.filter(
            StoredKey.machine == machine,
            StoredKey.material == material,
            StoredKey.tool.has(StoredTool.tool_type == tool_type),
            StoredKey.tool.has(StoredTool.tool_diameter == tool_diameter),
            ~StoredKey.tool.has(StoredTool.tool.in_(excluded_tools))).all()
        if not keys:
            raise ValueError("No relevant maps stored.")

        try:
            t = IDRetrieval(producer=client,
                            count=len(keys))
            db.session.add(t)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError from e
        return [
            (key.map_id, key.public_key_n, key.private_key_p, key.private_key_q)
            for key in keys
        ]
