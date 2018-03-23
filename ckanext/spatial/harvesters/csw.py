import re
import urllib
import urlparse
import os
import logging

from ckan import model

from ckan.plugins.core import SingletonPlugin, implements

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.model import HarvestObjectExtra as HOExtra

from ckanext.spatial.lib.csw_client import CswService
from ckanext.spatial.harvesters.base import SpatialHarvester, text_traceback


class CSWHarvester(SpatialHarvester, SingletonPlugin):
    '''
    A Harvester for CSW servers
    '''
    implements(IHarvester)

    csw=None

    def info(self):
        return {
            'name': 'csw',
            'title': 'CSW Server',
            'description': 'A server that implements OGC\'s Catalog Service for the Web (CSW) standard'
            }


    def get_original_url(self, harvest_object_id):
        obj = model.Session.query(HarvestObject).\
                                    filter(HarvestObject.id==harvest_object_id).\
                                    first()

        parts = urlparse.urlparse(obj.source.url)

        params = {
            'SERVICE': 'CSW',
            'VERSION': '2.0.2',
            'REQUEST': 'GetRecordById',
            'OUTPUTSCHEMA': 'http://www.isotc211.org/2005/gmd',
            'OUTPUTFORMAT':'application/xml' ,
            'ID': obj.guid
        }

        url = urlparse.urlunparse((
            parts.scheme,
            parts.netloc,
            parts.path,
            None,
            urllib.urlencode(params),
            None
        ))

        return url

    def output_schema(self):
        return 'gmd'

    
    def get_constraints(self, harvest_job):
        '''Returns the CSW constraints that should be used during gather stage.
        Should be overwritten by sub-classes.
        '''
        return []

    def gather_stage(self, harvest_job):
        log = logging.getLogger(__name__ + '.CSW.gather')
        log.debug('CswHarvester gather_stage for job: %r at the URL >>>>> %s <<<<<', harvest_job,harvest_job.source.url)
        # Get source URL
        url = harvest_job.source.url
        log.debug('Config: %r', harvest_job.source.config)
        self._set_source_config(harvest_job.source.config)
        log.debug('CSW Harvester - gather stage - URL %s <<<<<<<', url)
        try:
            self._setup_csw_client(url)
        except Exception, e:
            self._save_gather_error('Error contacting the CSW server: %s' % e, harvest_job)
            return None

        query = model.Session.query(HarvestObject.guid, HarvestObject.package_id).\
                                    filter(HarvestObject.current==True).\
                                    filter(HarvestObject.harvest_source_id==harvest_job.source.id)

        allquery = model.Session.query(HarvestObject.guid,HarvestObject.package_id).filter(HarvestObject.current==True)
 
        guid_to_package_id = {}

        for guid, package_id in query:
            guid_to_package_id[guid] = package_id

        guids_in_db = set(guid_to_package_id.keys())

        gtp = {}
        for guid, package_id in allquery:
                gtp[guid] = package_id
        guids_in_all_db = set(gtp.keys())

        cql = self.source_config.get('cql')
        
        log.debug('Starting gathering for cql %s ', cql )
        guids_in_harvest = set()
        bc = 0
       
        #fcsw = open('/var/log/csw-id.txt','w')
        try:
            for identifier in self.csw.getidentifiers(page=10, outputschema=self.output_schema(), cql=cql, constraints=self.get_constraints(harvest_job)):
                try:
                    log.info('Got identifier %s from the CSW url %s', identifier,url)
		    # FOR TESTING - only gather 1 set -- GH 8/3/2017 
		    if bc > 50000:
			break

                    if identifier is None:
                        log.error('CSW returned identifier %r, skipping...' % identifier)
                        continue

                    if identifier in guids_in_harvest:
                        log.info('CSW returned duplicated identifier in harvest %r, skipping ..' % identifier)
                        continue

                    # fcsw.write(identifier + '\n')
                    bc = bc + 1
                    guids_in_harvest.add(identifier)

                except Exception, e:
                    self._save_gather_error('Error for the identifier %s [%r]' % (identifier,e), harvest_job)
                    continue

        except Exception, e:
            log.error('Exception: %s' % text_traceback())
            self._save_gather_error('Error gathering the identifiers from the CSW server [%s]' % str(e), harvest_job)
            return None

        # fcsw.close()
        log.info('Guids in harvest count %d ', bc)

        new = guids_in_harvest - guids_in_all_db
        delete = guids_in_db - guids_in_harvest
        change = guids_in_all_db & guids_in_harvest
      
#        new = guids_in_harvest - guids_in_db
#        delete = guids_in_db - guids_in_harvest
#        change = guids_in_db & guids_in_harvest
        
        log.info('Gather set counts New: %d Delete: %d Change: %d ', len(new), len(delete), len(change) )

        nc = 0
        cc = 0
        dc = 0

        ids = []
        for guid in new:
            try:
                obj = HarvestObject(guid=guid, job=harvest_job,
                	                extras=[HOExtra(key='status', value='new')])
                obj.save()
                ids.append(obj.id)
                nc = nc + 1
            
            except Exception, e:
                self._save_gather_error('Error in new insert')
                continue

        for guid in change:
            try:
                if gtp[guid]:
                    obj = HarvestObject(guid=guid, job=harvest_job,
                                package_id=gtp[guid],
                                extras=[HOExtra(key='status', value='change')])
                else:
                    obj = HarvestObject(guid=guid, job=harvest_job,
                	                extras=[HOExtra(key='status', value='change')])             
                cc = cc + 1
                obj.save()
                ids.append(obj.id)

            except Exception, e:
                self._save_gather_error('Error in change')
                continue

            
        for guid in delete:
            try:
                if guid_to_package_id[guid]:
                    obj = HarvestObject(guid=guid, job=harvest_job,
                                package_id=guid_to_package_id[guid],
                                extras=[HOExtra(key='status', value='delete')])
                else:
                    obj = HarvestObject(guid=guid, job=harvest_job,
                	                extras=[HOExtra(key='status', value='delete')])       
                model.Session.query(HarvestObject).\
                                    filter_by(guid=guid).\
                                    update({'current': False}, False)
                dc = dc + 1
                obj.save()
                ids.append(obj.id)
            
            except Exception, e:
                self._save_gather_error('Error in delete')
                continue
       
        log.info('Gather Sort complete')
        log.info('Total gather packages: %s new: %s change: %s delete: %s', bc,nc,cc,dc )

        if len(ids) == 0:
            self._save_gather_error('No records received from the CSW server', harvest_job)
            return None

        return ids

    def fetch_stage(self,harvest_object):

        status = self._get_object_extra(harvest_object, 'status')
        if status == 'delete':
            return True
        
        log = logging.getLogger(__name__ + '.CSW.fetch')
        log.debug('CswHarvester fetch_stage for object: %s', harvest_object.id)
        log.info('CswHarvester fetch_stage for object: %s at url %s', harvest_object.id, harvest_object.source.url)

        url = harvest_object.source.url
        try:
            self._setup_csw_client(url)
        except Exception, e:
            self._save_object_error('ErrorX contacting the CSW server: %s' % e,
                                    harvest_object)
            return False

        identifier = harvest_object.guid
        try:
  	    log.debug('output schema : %s', self.output_schema())

            record = self.csw.getrecordbyid([identifier], outputschema=self.output_schema())
        except Exception, e:
            self._save_object_error('Error getting the CSW record with GUID %s' % identifier, harvest_object)
            return False

        if record is None:
            self._save_object_error('Empty record for GUID %s' % identifier,
                                    harvest_object)
            return False

        try:
            # Save the fetch contents in the HarvestObject
            # Contents come from csw_client already declared and encoded as utf-8
            # Remove original XML declaration
            content = re.sub('<\?xml(.*)\?>', '', record['xml'])

            harvest_object.content = content.strip()
            harvest_object.save()
        except Exception,e:
            self._save_object_error('Error saving the harvest object for GUID %s [%r]' % \
                                    (identifier, e), harvest_object)
            return False

        log.debug('XML content saved %s', record['tree'])
        # log.debug('XML content saved (len %s)', len(record['xml']))
        return True

    def _setup_csw_client(self, url):
        self.csw = CswService(url)

