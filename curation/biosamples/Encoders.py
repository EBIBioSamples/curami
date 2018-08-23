from json import JSONEncoder
from datetime import datetime
from biosamples.Models import Sample, Attribute, Relationship, Curation, CurationLink


class ISODateTimeEncoder(JSONEncoder):
    def default(self, o):
        if not isinstance(o, datetime):
            raise Exception("The provided object is not a datetime")
        return o.strftime("%Y-%m-%dT%H:%M:%SZ%z")


class SampleEncoder(JSONEncoder):
    def default(self, o):
        if not isinstance(o, Sample):
            raise Exception("The provided object is not a Sample")

        attribute_list_encoder = AttributeListEncoder()
        relatioship_encoder = RelationshipEncoder()
        datetime_encoder = ISODateTimeEncoder()

        _dict = dict()
        _dict["accession"] = o.accession
        _dict["release"] = datetime_encoder.default(o.release)
        _dict["update"] = datetime_encoder.default(o.update)
        _dict["characteristics"] = attribute_list_encoder.default(o.attributes)
        _dict["relationships"] = [relatioship_encoder.default(rel) for rel in o.relations]
        _dict["externalReferences"] = o.external_references
        _dict["organization"] = o.organizations
        _dict["contact"] = o.contacts
        return _dict


class AttributeEncoder(JSONEncoder):
    def default(self, o):
        if not isinstance(o, Attribute):
            raise Exception("The provided object is not an Attribute")

        _dict = dict()
        _dict["type"] = o.name
        _dict["text"] = o.value
        _dict["iri"] = o.iris
        _dict["unit"] = o.unit
        return _dict


class RelationshipEncoder(JSONEncoder):
    def default(self, o):
        if not isinstance(o, Relationship):
            raise Exception("The provided object is not a Relationship")

        _dict = dict()
        _dict["source"] = o.source
        _dict["type"] = o.type
        _dict["target"] = o.target


class AttributeListEncoder(JSONEncoder):

    def default(self, o):

        if not isinstance(o, list):
            return JSONEncoder.default(self, o)

        attr_encoder = AttributeEncoder()
        _dict = dict()
        for attr in o:
            if not isinstance(attr, Attribute):
                raise Exception("The provided list contains a non attribute object")

            attr_dict = attr_encoder.default(attr)
            attr_dict.pop("type", None)
            _dict.setdefault(attr.name, []).append(attr_dict)

        return _dict


class ExternalReferenceEncoder(JSONEncoder):
    def default(self, o):
        _dict = {"url": o["url"]}
        return _dict


class CurationObjectEncoder(JSONEncoder):
    def default(self, o):
        if not isinstance(o, Curation):
            return JSONEncoder.default(self, o)

        _dict = dict()
        _dict["curation"] = dict()
        _dict["curation"]["attributesPre"] = o.attr_pre
        _dict["curation"]["attributesPost"] = o.attr_post
        _dict["curation"]["externalReferencesPre"] = o.rel_pre
        _dict["curation"]["externalReferencesPost"] = o.rel_post
        _dict["domain"] = o.domain
        return _dict

class CurationLinkEncoder(JSONEncoder):
    def default(self, o):
        if not isinstance(o, CurationLink):
            return JSONEncoder.default(self, o)

        curation_object = o.curation
        _dict = dict()
        _dict["sample"] = o.accession
        _dict["curation"] = dict()
        _dict["curation"]["attributesPre"] = curation_object.attr_pre
        _dict["curation"]["attributesPost"] = curation_object.attr_post
        _dict["curation"]["externalReferencesPre"] = curation_object.rel_pre
        _dict["curation"]["externalReferencesPost"] = curation_object.rel_post
        _dict["domain"] = curation_object.domain
        return _dict
