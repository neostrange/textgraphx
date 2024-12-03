from abc import ABC
from abc import ABC, abstractmethod


class DocumentImporter(ABC):
    def __init__(self, id, data, content, neo4j_repository):
        self.id = id
        self.data = data
        self.content = content
        self.neo4j_repository = neo4j_repository

    @abstractmethod
    def get_query(self):
        pass

    @abstractmethod
    def get_params(self):
        pass

    def execute_query(self, query, params):
        return self.neo4j_repository.execute_query(query, params)

    def import_document(self):
        query = self.get_query()
        params = self.get_params()
        try:
            results = self.execute_query(query, params)
            return results
        except Exception as e:
            print(f"Error importing document: {e}")
            return None
        
    def __str__(self):
        return f"DocumentImporter(id={self.id}, data={self.data}, content={self.content})"

class MeantimeXMLImporter(DocumentImporter):
    def get_query(self):
        # Return the Cypher query specific to MEANTIME XML documents
        return """ WITH $data
        AS xmlString 
        WITH apoc.xml.parse(xmlString) AS value
        UNWIND [item in value._children where item._type ="nafHeader"] AS nafHeader
        UNWIND [item in value._children where item._type ="raw"] AS raw
        UNWIND [item in nafHeader._children where item._type = "fileDesc"] AS fileDesc
        UNWIND [item in nafHeader._children where item._type = "public"] AS public
        WITH  fileDesc.author as author, fileDesc.creationtime as creationtime, fileDesc.filename as filename, fileDesc.filetype as filetype, fileDesc.title as title, public.publicId as publicId, public.uri as uri, raw._text as text
        MERGE (at:AnnotatedText {id: $id}) set at.author = author, at.creationtime = creationtime, at.filename = filename, at.filetype = filetype, at.title = title, at.publicId = publicId, at.uri = uri, at.text = $text
        """

    def get_params(self):
        # Return the parameters specific to MEANTIME XML documents
        return {"id": self.id, "data": self.data, "text": self.content}

# # Usage
# driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
# neo4j_repository = Neo4jRepository(driver)
# document_importer = None
# if document_type == "MEANTIME_XML":
#     document_importer = MeantimeXMLImporter(id, data, content, neo4j_repository)
# elif document_type == "ANOTHER_TYPE":
#     document_importer = AnotherDocumentImporter(id, data, content, neo4j_repository)

# if document_importer:
#     document_importer.import_document()