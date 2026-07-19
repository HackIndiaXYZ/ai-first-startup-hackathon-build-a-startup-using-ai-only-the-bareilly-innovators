import os
import sys
import json
import logging
import networkx as nx

logger = logging.getLogger("sivi.knowledge_graph")

class KnowledgeGraphManager:
    """
    Sivi's Structural Memory. 
    Uses NetworkX to build a directed graph of entities and relationships.
    This provides deeper contextual awareness than raw vector RAG.
    """
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.data_dir = os.path.join(os.path.dirname(sys.executable), "data")
        else:
            self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
            
        os.makedirs(self.data_dir, exist_ok=True)
        self.graph_path = os.path.join(self.data_dir, "sivi_graph.json")
        self.graph = nx.DiGraph()
        self._load_graph()

    def _load_graph(self):
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
                logger.info(f"Loaded Knowledge Graph with {self.graph.number_of_nodes()} nodes.")
            except Exception as e:
                logger.error(f"Failed to load Knowledge Graph: {e}")
                self.graph = nx.DiGraph()

    def _save_graph(self):
        try:
            data = nx.node_link_data(self.graph)
            with open(self.graph_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save Knowledge Graph: {e}")

    def add_relation(self, subject: str, predicate: str, object_entity: str) -> str:
        """Adds a triple to the graph: (Subject) -> [Predicate] -> (Object)"""
        subject = subject.strip().lower()
        object_entity = object_entity.strip().lower()
        predicate = predicate.strip().lower()
        
        self.graph.add_node(subject)
        self.graph.add_node(object_entity)
        self.graph.add_edge(subject, object_entity, relation=predicate)
        self._save_graph()
        
        return f"Learned a new connection: {subject} -> {predicate} -> {object_entity}"

    def query_entity(self, entity: str) -> str:
        """Retrieves all 1-hop connections for a specific entity."""
        entity = entity.strip().lower()
        if entity not in self.graph:
            return f"I don't have any structural knowledge about '{entity}' yet."
            
        connections = []
        # Outgoing edges (What this entity does/is)
        for target in self.graph.successors(entity):
            rel = self.graph.edges[entity, target].get('relation', 'connected to')
            connections.append(f"- {entity} {rel} {target}")
            
        # Incoming edges (Things related TO this entity)
        for source in self.graph.predecessors(entity):
            rel = self.graph.edges[source, entity].get('relation', 'connected to')
            connections.append(f"- {source} {rel} {entity}")
            
        if not connections:
            return f"'{entity}' exists in my memory, but has no clear connections."
            
        result = f"Here is what I know structurally about '{entity}':\n" + "\n".join(connections)
        return result

knowledge_graph = KnowledgeGraphManager()
