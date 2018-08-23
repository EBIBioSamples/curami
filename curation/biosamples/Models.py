from datetime import datetime


class Sample:
    def __init__(self, sample=None, name=None, release=datetime.utcnow(), update=datetime.utcnow(),
                 attributes=None, relationships=None, external_references=None, organizations=None, contacts=None,
                 publications=None, domain=None):
        self.sample = sample
        self.name = name
        self.release = release
        self.update = update
        self.domain = domain
        self.attributes = [] if attributes is None else attributes
        self.relations = [] if relationships is None else relationships
        self.external_references = [] if external_references is None else external_references
        self.organizations = [] if organizations is None else organizations
        self.contacts = [] if contacts is None else contacts
        self.publications = [] if publications is None else publications

    def __str__(self):
        return "Sample {}".format(self.accession)


class Attribute:
    def __init__(self, name=None, value=None, iris=None, unit=None):
        if name is None or value is None:
            raise Exception("Attribute need at least a type and a value")
        self.name = name
        self.value = value
        self.iris = [] if iris is None else iris
        self.unit = unit


class Relationship:
    def __init__(self, source=None, rel_type=None, target=None):
        if source is None or rel_type is None or target is None:
            raise Exception("You need to provide a source, "
                            "a target and the rel_type of relation to make it valid")
        self.source = source
        self.rel_type = type
        self.target = target


class Curation:
    def __init__(self, attributes_pre=None, attributes_post=None,
                 external_references_pre=None, external_references_post=None, domain=None):
        if domain is None:
            raise Exception("A domain is needed to create a curation object")

        self.attr_pre = [] if attributes_pre is None else attributes_pre
        self.attr_post = [] if attributes_post is None else attributes_post
        self.rel_pre = [] if external_references_pre is None else external_references_pre
        self.rel_post = [] if external_references_post is None else external_references_post
        self.domain = domain


class CurationLink:
    def __init__(self, accession=None, curation=None):

        if accession is None:
            raise Exception("An accession is needed to create a curation link")

        if curation is None or type(curation) is not Curation:
            raise Exception("You need to provide a curation object as part of a curation link")

        self.accession = accession
        self.curation = curation