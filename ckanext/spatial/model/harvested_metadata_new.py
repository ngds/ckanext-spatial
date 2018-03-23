from lxml import etree

import logging
log = logging.getLogger(__name__)


class MappedXmlObject(object):
    elements = []


class MappedXmlDocument(MappedXmlObject):
    def __init__(self, xml_str=None, xml_tree=None):
        assert (xml_str or xml_tree is not None), 'Must provide some XML in one format or another'
        self.xml_str = xml_str
        self.xml_tree = xml_tree

    def read_values(self):
        '''For all of the elements listed, finds the values of them in the
        XML and returns them.'''
        values = {}
        tree = self.get_xml_tree()
        for element in self.elements:
            values[element.name] = element.read_value(tree)
        self.infer_values(values)
        return values

    def read_value(self, name):
        '''For the given element name, find the value in the XML and return
        it.
        '''
        tree = self.get_xml_tree()
        for element in self.elements:
            if element.name == name:
                return element.read_value(tree)
        raise KeyError

    def get_xml_tree(self):
        if self.xml_tree is None:
            parser = etree.XMLParser(remove_blank_text=True)
            if type(self.xml_str) == unicode:
                xml_str = self.xml_str.encode('utf8')
            else:
                xml_str = self.xml_str
            self.xml_tree = etree.fromstring(xml_str, parser=parser)
        return self.xml_tree

    def infer_values(self, values):
        pass


class MappedXmlElement(MappedXmlObject):
    namespaces = {}

    def __init__(self, name, search_paths=[], multiplicity="*", elements=[]):
        self.name = name
        self.search_paths = search_paths
        self.multiplicity = multiplicity
        self.elements = elements or self.elements

    def read_value(self, tree):
        values = []
        for xpath in self.get_search_paths():
            elements = self.get_elements(tree, xpath)
            values = self.get_values(elements)
            ''' only catches values on first xpath that has values; consider changing behavior to catch values on all xpaths, and then concatenate in fix_multiplicity if the properity is supposed to be single valued '''
            if values:
                break
        return self.fix_multiplicity(values)

    def get_search_paths(self):
        if type(self.search_paths) != type([]):
            search_paths = [self.search_paths]
        else:
            search_paths = self.search_paths
        return search_paths

    def get_elements(self, tree, xpath):
        return tree.xpath(xpath, namespaces=self.namespaces)

    def get_values(self, elements):
        values = []
        if len(elements) == 0:
            pass
        else:
            for element in elements:
                value = self.get_value(element)
                values.append(value)
        return values

    def get_value(self, element):
        if self.elements:
            value = {}
            for child in self.elements:
                value[child.name] = child.read_value(element)
            return value
        elif type(element) == etree._ElementStringResult:
            value = str(element)
        elif type(element) == etree._ElementUnicodeResult:
            value = unicode(element)
        else:
            value = self.element_tostring(element)
        return value

    def element_tostring(self, element):
        return etree.tostring(element, pretty_print=False)

    def fix_multiplicity(self, values):
        '''
        When a field contains multiple values, yet the spec says
        it should contain only one, then return just the first value,
        rather than a list.

        In the ISO19115 specification, multiplicity relates to:
        * 'Association Cardinality'
        * 'Obligation/Condition' & 'Maximum Occurence'
        '''
        if self.multiplicity == "0":
            # 0 = None
            if values:
                log.warn("Values found for element '%s' when multiplicity should be 0: %s",  self.name, values)
            return ""
        
        #smr add catch to flag elements that don't get processed
        elif self.multiplicity == "-1":
            # 0 = None
            if values:
                log.warn("Values found for element '%s' but these were not processed",  self.name, values)
            return ""
        elif self.multiplicity == "1":
            # 1 = Mandatory, maximum 1 = Exactly one
            if not values:
                log.warn("Value not found for element '%s'" % self.name)
                return ''
            return values[0]
        elif self.multiplicity == "*":
            # * = 0..* = zero or more
            return values
        elif self.multiplicity == "0..1":
            # 0..1 = Mandatory, maximum 1 = optional (zero or one)
            if values:
                return values[0]
            else:
                return ""
        elif self.multiplicity == "1..*":
            # 1..* = one or more
            return values
        else:
            log.warning('Multiplicity not specified for element: %s',
                        self.name)
            return values


class ISOElement(MappedXmlElement):
    # declare gml and gml3.2 because either one might show up in instances ...

    namespaces = {
       "gts": "http://www.isotc211.org/2005/gts",
       "gml": "http://www.opengis.net/gml",
       "gml32": "http://www.opengis.net/gml/3.2",
       "gmx": "http://www.isotc211.org/2005/gmx",
       "gsr": "http://www.isotc211.org/2005/gsr",
       "gss": "http://www.isotc211.org/2005/gss",
       "gco": "http://www.isotc211.org/2005/gco",
       "gmd": "http://www.isotc211.org/2005/gmd",
       "srv": "http://www.isotc211.org/2005/srv",
       "xlink": "http://www.w3.org/1999/xlink",
       "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }

#process CI_OnlineResource
class ISOResourceLocator(ISOElement):
    elements = [
        ISOElement(
            name="url",
            search_paths=[
                "gmd:linkage/gmd:URL/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="function",
            search_paths=[
                "gmd:function/gmd:CI_OnLineFunctionCode/@codeListValue",
            ],
            multiplicity="0..1",
        ),
       
        #smr addition
        ISOElement(
            name="functionText",
            search_paths=[
                "gmd:function/gmd:CI_OnLineFunctionCode/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="functionCodeList",
            search_paths=[
                "gmd:function/gmd:CI_OnLineFunctionCode/@codeList",
            ],
            multiplicity="0..1",
        ),
        #end SMR insert
        
        ISOElement(
            name="name",
            search_paths=[
                "gmd:name/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="description",
            search_paths=[
                "gmd:description/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="protocol",
            search_paths=[
                "gmd:protocol/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
    ]


# SMR addition
class ISOPostalAddress(ISOElement):
    elements = [
        ISOElement(
            name="deliveryPoint",
            search_paths=[
                        "gmd:address/gmd:CI_Address/gmd:deliveryPoint/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
                
        ISOElement(
            name="city",
            search_paths=[
                        "gmd:address/gmd:CI_Address/gmd:city/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),      
                
        ISOElement(
            name="administrativeArea",
            search_paths=[
                        "gmd:address/gmd:CI_Address/gmd:administrativeArea/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        ISOElement(
            name="postalCode",
            search_paths=[
                        "gmd:address/gmd:CI_Address/gmd:postalCode/gco:CharacterString/text()",
                    ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="country",
            search_paths=[
                        "gmd:address/gmd:CI_Address/gmd:country/gco:CharacterString/text()",
                    ],
            multiplicity="0..1",
        ),         
    ]
    
    # smr addition end 
class ISOResponsibleParty(ISOElement):

    elements = [
        ISOElement(
            name="individual-name",
            search_paths=[
                "gmd:individualName/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="organisation-name",
            search_paths=[
                "gmd:organisationName/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="position-name",
            search_paths=[
                "gmd:positionName/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="contact-info",
            search_paths=[
                "gmd:contactInfo/gmd:CI_Contact",
            ],
            multiplicity="0..1",
            elements = [
                ISOElement(
                    name="email",
                    search_paths=[
                        "gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString/text()",
                    ],
                    multiplicity="0..1",
                ),
                #SMR addition 
                # ignore facsimile numbers... 
                ISOElement(
                    name="telephoneVoice",
                    search_paths=[
                        "gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString/text()",
                    ],
                    multiplicity="*",
                ),
                
                ISOPostalAddress(
                    name = "postalAddress",
                    search_paths=[
                        "gmd:address/gmd:CI_Address",
                    ],
                    multiplicity="0..1",
                ),    
                # end smr addition 
                
                ISOResourceLocator(
                    name="online-resource",
                    search_paths=[
                        "gmd:onlineResource/gmd:CI_OnlineResource",
                    ],
                    multiplicity="0..1",
                ),

            ]
        ),
        ISOElement(
            name="role",
            search_paths=[
                "gmd:role/gmd:CI_RoleCode/@codeListValue",
            ],
            multiplicity="1",
        ),
        #smr  change multiplicity on role to 1 
        #smr addition add element text and codeSpace
        ISOElement(
            name="roleText",
            search_paths=[
                "gmd:role/gmd:CI_RoleCode/Text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="roleCodeSpace",
            search_paths=[
                "gmd:role/gmd:CI_RoleCode/@codeSpace",
            ],
            multiplicity="0..1",
        ), 
        #end smr addition
    ]

class ISODataFormat(ISOElement):

    elements = [
        ISOElement(
            name="name",
            search_paths=[
                "gmd:name/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="version",
            search_paths=[
                "gmd:version/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        #smr add to capture other text
        ISOElement(
            name="other-format-info",
            search_paths=[
                "gmd:amendmentNumber/gco:CharacterString/text()",
                "gmd:specification/gco:CharacterString/text()",
                "gmd:fileDecompressionTechnique/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
    ]


class ISOReferenceDate(ISOElement):

    elements = [
        ISOElement(
            name="type",
            search_paths=[
                "gmd:dateType/gmd:CI_DateTypeCode/@codeListValue",
                "gmd:dateType/gmd:CI_DateTypeCode/text()",
            ],
            multiplicity="1",
        ),
        
        #smr add dateType codeList 
        ISOElement(
            name="type-codelist",
            search_paths=[
                "gmd:dateType/gmd:CI_DateTypeCode/@codeList",
            ],
            multiplicity="0..1",
        ),

         
        ISOElement(
            name="value",
            search_paths=[
                "gmd:date/gco:Date/text()",
                "gmd:date/gco:DateTime/text()",
            ],
            multiplicity="1",
        ),
    ]

class ISOCoupledResources(ISOElement):
    #assumes that operatesOn is implemented as an xlink href. should log a warning if there is an inline MD_DataIdentification
    #this appears to be junk; the apiso.xsd implementation of service metdaata does not follow the UML in ISO19119.
    elements = [
        #smr fix multiplicities
        ISOElement(
            name="title",
            search_paths=[
                "@xlink:title",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="href",
            search_paths=[
                "@xlink:href",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="uuid",
            search_paths=[
                "@uuidref",
            ],
            multiplicity="0..1",
        ),
        #shouldn't have inline MD_DataIdenfication; multipclicity 0 will put warning in log 
        ISOElement(
            name="coupled-inline-dataIdentification",
            search_paths=["MD_DataIdentification",
            ],
            multiplicity="0",
        ),
    ]


class ISOBoundingBox(ISOElement):

    elements = [
        ISOElement(
            name="west",
            search_paths=[
                "gmd:westBoundLongitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="east",
            search_paths=[
                "gmd:eastBoundLongitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="north",
            search_paths=[
                "gmd:northBoundLatitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="south",
            search_paths=[
                "gmd:southBoundLatitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
    ]

class ISOBrowseGraphic(ISOElement):

    elements = [
        ISOElement(
            name="file",
            search_paths=[
                "gmd:fileName/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="description",
            search_paths=[
                "gmd:fileDescription/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="type",
            search_paths=[
                "gmd:fileType/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
    ]


class ISOKeyword(ISOElement):

    elements = [
        ISOElement(
            name="keyword",
            search_paths=[
                "gmd:keyword/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="type",
            search_paths=[
                "gmd:type/gmd:MD_KeywordTypeCode/@codeListValue",
                "gmd:type/gmd:MD_KeywordTypeCode/text()",
            ],
            multiplicity="0..1",
        ),
        
        #smr add typeCode codelist '''
        ISOElement(
            name="type-codelist",
            search_paths=[
                "gmd:type/gmd:MD_KeywordTypeCode/@codeList",
            ],
            multiplicity="0..1",
        ),
        
        # smr add thesaurus information 
        
        ISOElement(
            name="thesaurus-title",
            search_paths=[
                "gmd:thesaurusName/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        ISOElement(
            name="thesaurus-identifier",
            search_paths=[
                "gmd:thesaurusName/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        # end thesaurus information 

        # If more Thesaurus information is needed at some point, this is the
        # place to add it
   ]


class ISOUsage(ISOElement):

    elements = [
        ISOElement(
            name="usage",
            search_paths=[
                "gmd:specificUsage/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOResponsibleParty(
            name="contact-info",
            search_paths=[
                "gmd:userContactInfo/gmd:CI_ResponsibleParty",
            ],
            multiplicity="0..1",
        ),
        
        #smr add usageDateTime and  limitations
        ISOElement(
            name="usage-limitations",
            search_paths=[
                "gmd:userDeterminedLimitations/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        ISOElement(
            name="usage-date",
            search_paths=[
                "gmd:usageDateTime/gco:DateTime/text()",
            ],
            multiplicity="0..1",
        ),
   ]


class ISOAggregationInfo(ISOElement):
    elements = [
        ISOElement(
            name="aggregate-dataset-name",
            search_paths=[
                "gmd:aggregateDatasetName/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="aggregate-dataset-identifier",
            search_paths=[
                "gmd:aggregateDatasetIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="association-type-text",
            search_paths=[
                "gmd:associationType/gmd:DS_AssociationTypeCode/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="association-type",
            search_paths=[
                "gmd:associationType/gmd:DS_AssociationTypeCode/@codeListValue",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="association-type-codelist",
            search_paths=[
                "gmd:associationType/gmd:DS_AssociationTypeCode/@codeList",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="initiative-type",
            search_paths=[
                "gmd:initiativeType/gmd:DS_InitiativeTypeCode/@codeListValue",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="initiative-type-text",
            search_paths=[
                "gmd:initiativeType/gmd:DS_InitiativeTypeCode/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="initiative-type-codelist",
            search_paths=[
                "gmd:initiativeType/gmd:DS_InitiativeTypeCode/@codeList",
            ],
            multiplicity="0..1",
        ),
   ]

#smr add
class ISOTransferOptions(ISOElement):
    elements = [
        ISOElement(
            name="unit-of-distribution",
            search_paths=[
                "gmd:unitsOfDistribution/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="transfer-size",
            search_paths=[
                "gmd:transferSize/gco:Real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOResourceLocator(
            name="online-distribution",
            search_paths=[
                "gmd:online/gmd:CI_OnlineResource",
            ],
            multiplicity="0..*",
        ),

        ISOElement(
            name="transfer-medium-name",
            search_paths=[
                "gmd:offLine/gmd:MD_Medium/gmd:name/gmd:MD_MediumNameCode/@codeListValue",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="transfer-medium-name-codelist",
            search_paths="gmd:offLine/gmd:MD_Medium/gmd:name/gmd:MD_MediumNameCode/@codeList",
            multiplicity="0..1",
        ),
        ISOElement(
            name="transfer-medium-note",
            search_paths="gmd:offLine/gmd:MD_Medium/gmd:mediumNote/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="transfer-medium-format",
            search_paths=[
                "gmd:offLine/gmd:MD_Medium/gmd:mediumFormat/gmd:MD_MediumFormatCode/@codeListValue",
            ],
            multiplicity="0..*",
        ),
        ISOElement(
            name="transfer-medium-format-codelist",
            search_paths=[
                "gmd:offLine/gmd:MD_Medium/gmd:mediumFormat/gmd:MD_MediumFormatCode/@codeList",
            ],
            multiplicity="0..*",
        ),
    ]
    
    
#smr add    
class ISOOrderProcess(ISOElement):
    elements = [
        ISOElement(
            name="fees",
            search_paths=[
                "gmd:fees/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="instructions",
            search_paths=[
                "gmd:orderingInstructions/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="available-datetime",
            search_paths=[
                "gmd:plannedAvailableDateTime/gco:DateTime/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="turn-around",
            search_paths=[
                "gmd:turnaround/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
    ]  
#smr add
class ISODistributorAccessOptions(ISOElement):
    elements = [
        ISOResponsibleParty(
            name="distributor-contact",
            search_paths=[
                "gmd:distributorContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="1",
        ),
        ISODataFormat(
            name="distributor-format",
            search_paths=[
                "gmd:distributorFormat/gmd:MD_Format",
            ],
            multiplicity="0..*",
        ),
        ISOTransferOptions(
            name="distributor-transfer-option",
            search_paths=[
                "gmd:distributorTransferOptions/gmd:MD_DigitalTransferOptions",
            ],
            multiplicity="0..*",
        ),
        ISOOrderProcess(
            name="distributor-order-process",
            search_paths=[
                "gmd:distributionOrderProcess/gmd:MD_StandardOrderProcess",
            ],
            multiplicity="0..*",
        ),   
    ]
   




#this is where everythign gets gathered together
class ISODocument(MappedXmlDocument):

    elements = [
        #file identifier (identifies the metadata record, not the described resoruce)
        ISOElement(
            name="guid",
            search_paths="gmd:fileIdentifier/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        
        #language
        ISOElement(
            name="metadata-language",
            search_paths=[
                "gmd:language/gmd:LanguageCode/@codeListValue"
            ],
            multiplicity="0..1",
        ),   
        # smr add codelist '''
        ISOElement(
            name="metadata-language-codeList",
            search_paths=[
                "gmd:language/gmd:LanguageCode/@codeList"
            ],
            multiplicity="0..1",
        ),

        
        # leaves out CharacterSet
        
        #metadata standard name and version
        ISOElement(
            name="metadata-standard-name",
            search_paths="gmd:metadataStandardName/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="metadata-standard-version",
            search_paths="gmd:metadataStandardVersion/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        
        # resource type from hierarchyLevel
        ISOElement(
            name="resource-type",
            search_paths=[
                "gmd:hierarchyLevel/gmd:MD_ScopeCode/@codeListValue"
            ],
            multiplicity="*",
        ),
        # smr add text for element 
        ISOElement(
            name="resource-type-text",
            search_paths=[
                "gmd:hierarchyLevel/gmd:MD_ScopeCode/text()",
            ],
            multiplicity="*",
        ),
        # smr add scopeCode codelist 
        ISOElement(
            name="resource-type-codelist",
            search_paths=[
                "gmd:hierarchyLevel/gmd:MD_ScopeCode/@codeList",
            ],
            multiplicity="*",
        ),
       
        
        # for USGIN hierarchy level name 
        ISOElement(
            name="resource-type-name",
            search_paths=[
                "gmd:hierarchyLevelName/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        # end insert 
        
        # correct the xpath for metadata point of contact, was mapped to identificationInfo POC which is the resource POC
        ISOResponsibleParty(
            name="metadata-point-of-contact",
            search_paths=[
                "gmd:contact/gmd:CI_ResponsibleParty"
            ],
            multiplicity="1..*",
        ),
        
        #metadata time stamp
        ISOElement(
            name="metadata-date",
            search_paths=[
                "gmd:dateStamp/gco:DateTime/text()",
                "gmd:dateStamp/gco:Date/text()",
            ],
            multiplicity="1",
        ),
        
        # smr add datasetURI; have to reconcile with MD_Identifier in information//CI_Citation
        ISOElement(
            name="other_ID",
            search_paths=[
                "gmd:dataSetURI/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        # don't process SpatialRepresentation; -1 multiplicity throws warning in the log
        ISOElement(
            name="spatial-representation",
            search_paths=[
                "gmd:spatialRepresentationInfo",
            ],
            multiplicity="-1",
        ),

        #spatial reference system
        ISOElement(
            name="spatial-reference-system",
            search_paths=[
                "gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        #smr add spatial reference system authority title '''
        ISOElement(
            name="srs-authority-title",
            search_paths=[
                "gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:authority/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        #smr add spatial reference system identifier codespace '''
        ISOElement(
            name="srs-codespace",
            search_paths=[
                "gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        ###### identificationInfo CI_Citation section ''''       
       
        # title
        ISOElement(
            name="title",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),
        
        #alternateTitle
        ISOElement(
            name="alternate-title",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:alternateTitle/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:alternateTitle/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        
        #resource reference dates
        ISOReferenceDate(
            name="dataset-reference-date",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date",
            ],
            multiplicity="1..*",
        ),
        
        #resource identifier; reconcole with DataSEtURI; inclued ISSN and ISBN here 
        ISOElement(
            name="unique-resource-identifier",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:ISBN/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:ISBN/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:ISSN/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:ISSN/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        # edition and editionDate are added in additional citation info
        
        #presentation forms
        ISOElement(
            name="presentation-form",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",

            ],
            multiplicity="*",
        ),
        # smr add codelist value '''
        ISOElement(
            name="presentation-form-codelist",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeList",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeList",

            ],
            multiplicity="*",
        ),

        #abstract for resource
        ISOElement(
            name="abstract",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:abstract/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),
        
        # smr add edition, edition date, series information, collective title into other citation details This is where the get values processing would need to look at all the xpaths, and concatenate results
         ISOElement(
            name="other-citation-details",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:edition/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:edition/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:editionDate/gco:Date/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:editionDate/gco:DateTime/text()"
                "gmd:identificationInfo/gmd:SV_ServiceIdentification/gmd:editionDate/gco:Date/text()",
                "gmd:identificationInfo/gmd:SV_ServiceIdentification/gmd:editionDate/gco:DateTime/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:series/gmd:CI_Series/gmd:name/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:series/gmd:CI_Series/gmd:name/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:series/gmd:CI_Series/gmd:issueIdentification/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:series/gmd:CI_Series/gmd:issueIdentification/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:series/gmd:CI_Series/gmd:page/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:series/gmd:CI_Series/gmd:page/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:otherCitationDetails/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:otherCitationDetails/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:collectiveTitle/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:collectiveTitle/gco:CharacterString/text()",               
            ],
            multiplicity="0..1",
        ),
        
        #resource purpose
        ISOElement(
            name="purpose",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:purpose/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:purpose/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        # resource credit smr add
        ISOElement(
            name="credit",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:credit/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:credit/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),

        
        # remove metadata contact from the search_paths for the resoruce POC
        ISOResponsibleParty(
            name="responsible-organisation",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="1..*",
        ),
        
        #updateFrequency
        ISOElement(
            name="frequency-of-update",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/text()",
            ],
            multiplicity="0..1",
        ),
        
        #maintenanceNote  **** need to work on other maintance properties
        ISOElement(
            name="maintenance-note",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceNote/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceNote/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        #progress code
        ISOElement(
            name="progress",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:status/gmd:MD_ProgressCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:status/gmd:MD_ProgressCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:status/gmd:MD_ProgressCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:status/gmd:MD_ProgressCode/text()",
            ],
            multiplicity="*",
        ),
        # smr add progressCode codelist 
        ISOElement(
            name="progress-codelist",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:status/gmd:MD_ProgressCode/@codeList",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:status/gmd:MD_ProgressCode/@codeList",
            ],
            multiplicity="*",
        ),
        
        #keywords
        ISOKeyword(
            name="keywords",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords",
            ],
            multiplicity="*"
        ),
        
        # smr-- this looks useless--gathers all keywords....??? 
        ISOElement(
            name="keyword-inspire-theme",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        # Deprecated: kept for backwards compatibilty
        ISOElement(
            name="keyword-controlled-other",
            search_paths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:keywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        
        # usage
        ISOUsage(
            name="usage",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceSpecificUsage/gmd:MD_Usage",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceSpecificUsage/gmd:MD_Usage",
            ],
            multiplicity="*"
        ),
        
        
        #### constraints section
        
        #other constraints statement
        ISOElement(
            name="limitations-on-public-access",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        #access constraints restrictioni codes
        ISOElement(
            name="access-constraints",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode/text()",
            ],
            multiplicity="*",
        ),
        #smr add use constraints restrictionCode
        ISOElement(
            name="use-constraints",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:useConstraints/gmd:MD_RestrictionCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:useConstraints/gmd:MD_RestrictionCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:useConstraints/gmd:MD_RestrictionCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:useConstraints/gmd:MD_RestrictionCode/text()",
            ],
            multiplicity="*",
        ),
        #smr change name from use-constraints to use limitations
        ISOElement(
            name="use-limitations",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        ###### end of constraints section
        
        #use to link to other resources. Aggregation info
        ISOAggregationInfo(
            name="aggregation-info",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:aggregationInfo/gmd:MD_AggregateInformation",
                "gmd:identificationInfo/gmd:SV_ServiceIdentification/gmd:aggregationInfo/gmd:MD_AggregateInformation",
            ],
            multiplicity="*"
        ),
        
        #service type
        ISOElement(
            name="spatial-data-service-type",
            search_paths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:serviceType/gco:LocalName/text()",
            ],
            multiplicity="0..1",
        ),
        #spatial resolution
        ISOElement(
            name="spatial-resolution",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="spatial-resolution-units",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/@uom",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/@uom",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="equivalent-scale",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/gco:Integer/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/gco:Integer/text()",
            ],
            multiplicity="*",
        ),
        
        
        #resource language
        ISOElement(
            name="dataset-language",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/text()",
            ],
            multiplicity="*",
        ),
        
        #topic category
        ISOElement(
            name="topic-category",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode/text()",
            ],
            multiplicity="*",
        ),
        
        #smr add environmentDescription in case someone uses that for software environment...
        ISOElement(
            name="environment-description",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:environmentDescription/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:environmentDescription/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        

        #extent, controlled-- move the geographicIdentifier values from extent-free-text to here...
        #  don't have a handler for EX_BoundingPolygon... should throw warning if have one
        ISOElement(
            name="extent-controlled",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        
        # smr put in xpath for EX_extent/description.
        ISOElement(
            name="extent-free-text",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:description/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:description/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        
        ISOBoundingBox(
            name="bbox",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox",
            ],
            multiplicity="*",
        ),
        
        
        #smr add time instant, for gml ns only; if is instant make extent-begin=extent-end..
        #also that gml3.2 should be invalid with gmd...
        ISOElement(
            name="temporal-extent-begin",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:beginPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:beginPosition/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimeInstant/gml:timePosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimeInstant/gml:timePosition/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="temporal-extent-end",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:endPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:endPosition/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimeInstant/gml:timePosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimeInstant/gml:timePosition/text()",
            ],
            multiplicity="*",
        ),
        
        #vertical extent has minimumValue and maximumValue properties. Have to check what this search_path actually does.
        ISOElement(
            name="vertical-extent",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:verticalElement/gmd:EX_VerticalExtent",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:verticalElement/gmd:EX_VerticalExtent",
            ],
            multiplicity="*",
        ),
        
        #supplemental informaiton on the dataset resource
        ISOElement(
            name="additional-information-source",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:supplementalInformation/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        #target of operatesOn is gmd:MD_DataIdentification; smr change name to avoid confusion with real coupled-resource
        ISOCoupledResources(
            name="operates-on-resource",
            search_paths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:operatesOn",
            ],
            multiplicity="*",
        ),
        
        #smr add
        # The apiso implementation of coupledResource only allows and operationName, an identifier (characterString), a scoped Name with codeSpace; note ScopedName breaks Entity/property capitalizaiton pattern
        ISOElement(
            name="sv-coupled-resource",
            search_paths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:coupledResource/srv:SV_CoupledResource",
            ],
            multiplicity="*",
            elements = [
                ISOCoupledResources(
                    name="resource-id",
                    search_paths=[
                        "srv:identifier/gco:CharacterString/text()"
                    ],
                    multiplicity="1",
                ),
                ISOElement(
                    name="coupled-scoped-name",
                    search_paths=[
                        "gco:ScopedName/text()"
                    ],
                    multiplicity="0..1",
                ),
                ISOElement(
                    name="operation-name",
                    search_paths=[
                        "srv:operationName/gco:CharacterString/text()"
                    ],
                    multiplicity="0..1"
                ),           
            ],
        ),

        
        #smr modify this to capture MD_Identification/resoruceFormat/MD_format. Distribuition specific formats need to be associated with the particular distirbution in case different options have different formats... USGIN profile recommends not using this form
        ISODataFormat(
            name="data-format",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceFormat/gmd:MD_Format",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceFormat/gmd:MD_Format",
            ],
            multiplicity="*",
        ),
        
        
        ############# Distribution section. logic will be necessary to map distribution consistnetly to the metadta JSON
        
        #smr add, access options, grouped by distributor. including linked format, digital transfer otpions and standard order process.  required if multiple distributors are present 
        ISODistributorAccessOptions(
            name="distributor-access-options",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor"
            ],
            multiplicity="0..*",
        ),
        #smr add
        ISOTransferOptions(
            name="distribution-transfer-options",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions",
            ],
            multiplicity="0..*",
        ),
        #smr add
        ISODataFormat(
            name="distribution-format",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat/gmd:MD_Format",
            ],
            multiplicity="0..*",
        ),
        
        #distributor contacts, only useful if there is only one distributor
        ISOResponsibleParty(
            name="distributor",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="*",
        ),
        
        #this needs to be refactored to bind distributors, formats, and transfer otpions...
        ISOResourceLocator(
            name="resource-locator",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource",
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorTransferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource"
            ],
            multiplicity="*",
        ),
        
        
        #collect all CI_OnlineResources in the identification section. Use to guess distribution URL...
        ISOResourceLocator(
            name="resource-locator-identification",
            search_paths=[
                "gmd:identificationInfo//gmd:CI_OnlineResource",
            ],
            multiplicity="*",
        ),
        
        
        #the handling of data quality here is complelely in inadequate for the possible complexity of DQ_DataQuality. Fortunatey it almost never shows up in metadata...
        #grab the specifications used for conformance results
        ISOElement(
            name="conformity-specification",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:specification",
            ],
            multiplicity="0..1",
        ),
        
        #grab the conformance result pass values. 
        ISOElement(
            name="conformity-pass",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:pass/gco:Boolean/text()",
            ],
            multiplicity="0..1",
        ),
        
        #quality conformity explanation
        ISOElement(
            name="conformity-explanation",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:explanation/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        #lineage statemend
        ISOElement(
            name="lineage",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:statement/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        
        #identificationInfo browseGraphic
        ISOBrowseGraphic(
            name="browse-graphic",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic",
            ],
            multiplicity="*",
        ),

    ]
    for elem in elements:
	    log.info("%s - %s",elem.name, elem.search_paths)

    def infer_values(self, values):
        # Todo: Infer name.
        self.infer_date_released(values)
        self.infer_date_updated(values)
        self.infer_date_created(values)
        self.infer_url(values)
        # Todo: Infer resources.
        self.infer_tags(values)
        self.infer_publisher(values)
        self.infer_contact(values)
        self.infer_contact_email(values)
        return values

    def infer_date_released(self, values):
        value = ''
        for date in values['dataset-reference-date']:
            if date['type'] == 'publication':
                value = date['value']
                break
        values['date-released'] = value

    def infer_date_updated(self, values):
        value = ''
        dates = []
        # Use last of several multiple revision dates.
        for date in values['dataset-reference-date']:
            if date['type'] == 'revision':
                dates.append(date['value'])

        if len(dates):
            if len(dates) > 1:
                dates.sort(reverse=True)
            value = dates[0]

        values['date-updated'] = value

    def infer_date_created(self, values):
        value = ''
        for date in values['dataset-reference-date']:
            if date['type'] == 'creation':
                value = date['value']
                break
        values['date-created'] = value

    def infer_url(self, values):
        value = ''
        for locator in values['resource-locator']:
            if locator['function'] == 'information':
                value = locator['url']
                break
        values['url'] = value

    def infer_tags(self, values):
        tags = []
        for key in ['keyword-inspire-theme', 'keyword-controlled-other']:
            for item in values[key]:
                if item not in tags:
                    tags.append(item)
        values['tags'] = tags

    def infer_publisher(self, values):
        value = ''
        for responsible_party in values['responsible-organisation']:
            if responsible_party['role'] == 'publisher':
                value = responsible_party['organisation-name']
            if value:
                break
        values['publisher'] = value

    def infer_contact(self, values):
        value = ''
        for responsible_party in values['responsible-organisation']:
            value = responsible_party['organisation-name']
            if value:
                break
        values['contact'] = value

    def infer_contact_email(self, values):
        value = ''
        for responsible_party in values['responsible-organisation']:
            if isinstance(responsible_party, dict) and \
               isinstance(responsible_party.get('contact-info'), dict) and \
               responsible_party['contact-info'].has_key('email'):
                value = responsible_party['contact-info']['email']
                if value:
                    break
        values['contact-email'] = value


class GeminiDocument(ISODocument):
    '''
    For backwards compatibility
    '''
