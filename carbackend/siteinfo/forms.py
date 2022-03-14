import json

from django.conf import settings
from django import forms
from django.forms import ModelForm, Form, FileField, TextInput
from django.forms import formset_factory
from .models import SiteInfoUpdate, InfoFileLocks
from . import utils

from datetime import datetime
import os
import re
import requests
_this_year = datetime.today().year
_base_field_width = '98%'


class SiteInfoUpdateForm(ModelForm):
    class Meta:
        model = SiteInfoUpdate
        fields = ['release_lag',
                  'location',
                  'contact',
                  'site_reference',
                  'data_reference']

    @classmethod
    def fixed_fields(cls):
        return tuple(f for f in SiteInfoUpdate.standard_fields() if f not in cls.Meta.fields)

    # def save(self, user, site_info, commit=True):
    #     data = self.cleaned_data
    #     data['user_updated'] = user
    #     for field in self.fixed_fields():
    #         data[field] = site_info[field]
    #     super().save(commit=commit)

    def clean(self):
        cleaned_data = super().clean()
        contact_re = re.compile(r'.+<.+@.+>(\s*;.+<.+@.+>)*\s*$')
        if not contact_re.match(cleaned_data.get('contact', '')):
            self.add_error('contact', 'Must have format "Name <email>" (no quotes) or "Name1 <email1>; Name2 <email2>"')
        if cleaned_data['release_lag'] > utils.get_max_release_lag():
            self.add_error('release_lag', 'Release lag cannot be greater than {} days'.format(utils.get_max_release_lag()))

        return cleaned_data


class SiteInfoUpdateStaffForm(SiteInfoUpdateForm):
    class Meta:
        model = SiteInfoUpdate
        fields = ['long_name',
                  'data_doi',
                  'data_revision',
                  'release_lag',
                  'location',
                  'contact',
                  'site_reference',
                  'data_reference']
        widgets = {
            'data_doi': TextInput()
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('data_doi', '').startswith('10.'):
            self.add_error('data_doi', 'DOI must start with "10." (do not include leading "doi.org" or the like)')
        cleaned_data['data_doi'] = cleaned_data.get('data_doi', '').strip()  # just in case, make sure no surrounding whitespace
        return cleaned_data


def _get_flag_name_choices():
    with open(settings.RELEASE_FLAGS_DEF_FILE) as f:
        definitions = tuple(json.load(f)['definitions'].keys())
    defs_long_form = {
        'ils': 'Problem with ILS',
        'tracking': 'Problem with solar tracker',
        'surface pressure': 'Error in surface pressure',
        'other': 'Other'
    }
    return [(k, defs_long_form[k]) for k in definitions]


def _get_flag_values():
    with open(settings.RELEASE_FLAGS_DEF_FILE) as f:
        return json.load(f)['definitions']


class MetadataAbstractForm(forms.Form):
    # Override this with field names as keys and values = lists
    # of values considered to be null/empty inputs. Used to determine
    # if the whole form is an empty one.
    _null_values = dict()

    def to_dict(self) -> dict:
        """Convert this form into a JSON dictionary, correctly formatted for the DOI metadata."""
        raise NotImplementedError('Must implement the to_dict method on a MetadataAbstractForm subclass')

    @classmethod
    def cite_schema_to_dict(cls, cite_schema_dict: dict) -> dict:
        """Convert the DOI metadata JSON dict into one that can be given as this form's initial value"""
        raise NotImplementedError('Must implement the to_dict method on a cite_schema_to_dict subclass')

    def is_valid(self):
        # This needed overridden to handle an edge case with the javascript: if you have a non-empty form, then
        # delete it, and an empty form takes its place, because the empty form is now in the position where the
        # non-empty one was, Django assumes that it should have the initial values of the non-empty form, and so
        # incorrectly sees it as having changed.
        #
        # Here, we ignore the bound initial values and just check if all of the forms inputs are their default values.
        # If so, it is an empty form, so we set the cleaned data to be empty and skip validation. Otherwise, we let
        # Django do its normal validation process.
        if self.is_empty():
            self.cleaned_data = dict()
            return True
        else:
            return super().is_valid()

    def is_empty(self):
        for name, field in self.fields.items():
            prefixed_name = self.add_prefix(name)
            data_value = field.widget.value_from_datadict(self.data, self.files, prefixed_name)
            if data_value not in self._null_values.get(name, (None, '', '-')):
                return False

        return True


class SiteDoiForm(forms.Form):
    site = forms.CharField(
        label='Full site name & country code',
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: Ascension Island (SH)',
            'style': f'width:{_base_field_width};'
        })
    )

    location_place = forms.CharField(
        label='Name of site location (optional)',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: Arlane Tracking Station (AC)',
            'style': f'width:{_base_field_width};'
        })
    )

    location_latitude = forms.CharField(
        label='Site latitude (optional)',
        help_text='Latitude in degrees, south is negative.',
        widget=forms.TextInput(attrs={
            'placeholder': 'South is negative',
            'style': f'width:{_base_field_width};'
        })
    )

    location_longitude = forms.CharField(
        label='Site longitude (optional)',
        help_text='Longitude in degrees, west is negative.',
        widget=forms.TextInput(attrs={
            'placeholder': 'West is negative',
            'style': f'width:{_base_field_width};'
        })
    )

    def clean_location_latitude(self):
        return self._clean_latlon('location_latitude', 'Site latitude', -90.0, 90.0)

    def clean_location_longitude(self):
        return self._clean_latlon('location_longitude', 'Site longitude', -180.0, 180.0)

    def _clean_latlon(self, key, descr, minval, maxval):
        data = self.cleaned_data[key]
        try:
            v = float(data)
        except ValueError:
            raise forms.ValidationError(f'{descr} must be a valid numeric value', 'bad_number')

        if v < minval or v > maxval:
            raise forms.ValidationError(f'{descr} must be between {minval:.1f} and {maxval:.1f}')

        # Keep it as a string, that's how it is stored in the JSON
        return data

    def add_form_to_json(self, doi_metadata, data_revision):
        doi_metadata['titles'] = [{'title': f'TCCON data from {self.cleaned_data["site"]}, '
                                            f'Release GGG2020.{data_revision}'}]

        geo_data = {'geoLocationPoint': {
            'pointLongitude': self.cleaned_data['location_longitude'],
            'pointLatitude': self.cleaned_data['location_latitude']
        }}

        if self.cleaned_data.get('location_place') is not None:
            geo_data['geoLocationPlace'] = self.cleaned_data['location_place']

        doi_metadata['geoLocations'] = [geo_data]

    @classmethod
    def json_to_dict(cls, doi_metadata):
        title = doi_metadata['titles'][0]['title']
        if 'geoLocations' in doi_metadata:
            geo_data = doi_metadata['geoLocations'][0]
        else:
            geo_data = {'geoLocationPoint': {'pointLatitude': None, 'pointLongitude': None}}
        return {
            'site': re.search(r'TCCON data from (.+), Release GGG2020', title).group(1),
            'location_place': geo_data.get('geoLocationPlace', None),
            'location_longitude': geo_data['geoLocationPoint']['pointLongitude'],
            'location_latitude': geo_data['geoLocationPoint']['pointLatitude'],
        }

    @classmethod
    def get_form_from_json(cls, doi_metadata):
        initial_data = cls.json_to_dict(doi_metadata)
        return cls(initial=initial_data)

    @classmethod
    def prettify_column_name(cls, colname):
        return colname


class CreatorForm(MetadataAbstractForm):
    family_name = forms.CharField(
        label='Family name',
        help_text='For individuals, give the family name. For institutions, research groups, or other entities, put the full name here and leave "given name" blank.',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter family name here',
            'style': f'width:{_base_field_width};'
        })
    )

    given_name = forms.CharField(
        label='Given name(s)',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter given name(s) or initials here.',
            'style': f'width:{_base_field_width};'
        })
    )

    affiliation = forms.CharField(
        label='Affiliation (optional)',
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter affiliation (e.g. institute, city, [state], country) here',
            'style': f'width:{_base_field_width}; height:3rem;'
        })
    )

    affiliation_id = forms.CharField(
        required=False, # required in certain circumstances, handled in `clean()`
        label='Affiliation identifier',
        help_text='An identifier from ror.org, the part of the URL after ror.org/. E.g. if you look up Caltech, the URL is https://ror.org/05dxps055, so enter 05dxps055. If you cannot find the institution on ror.org, enter N/A',
        widget=forms.TextInput(attrs={
            'placeholder': 'ID from ror.org (e.g 05dxps055)',
            'style': f'width:{_base_field_width}'
        })
    )

    orcid = forms.CharField(
        label='ORCID (optional)',
        required=False,
        help_text='An ORCID usually has the form NNNN-NNNN-NNNN-NNNN, i.e. 16 numbers, though letters are included occasionally',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter ORCID here',
            'style': f'width:{_base_field_width};'
        })
    )

    researcher_id = forms.CharField(
        label='Researcher ID (optional)',
        required=False,
        help_text='A researcher ID usually has the form X-NNNN-NNNN, where X is a letter and N a number',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter Researcher ID here',
            'style': f'width:{_base_field_width};'
        })
    )

    is_not_person = forms.BooleanField(
        label='Institution/group?',
        initial=False,
        help_text='Check if this is an institution, group, or other entity, rather than an individual person.',
        widget=forms.CheckboxInput(attrs={
            'style': 'width: 1rem;'
        })
    )

    _null_values = {'is_not_person': [False]}

    def to_dict(self):
        data = self.cleaned_data
        json_dict = {
            'affiliation': [{'name': data['affiliation']}],
            'nameIdentifiers': []
        }
        affil_id = data.get('affiliation_id', None)
        if affil_id and affil_id != 'N/A':
            json_dict['affiliation'][0]['affiliationIdentifier'] = f'https://ror.org/{affil_id}'
            json_dict['affiliation'][0]['affiliationIdentifierScheme'] = 'ROR'
        elif affil_id == 'N/A':
            json_dict['affiliation'][0]['affiliationIdentifier'] = affil_id
            json_dict['affiliation'][0]['affiliationIdentifierScheme'] = 'N/A'

        if data['is_not_person']:
            json_dict['name'] = data['family_name']
        else:
            json_dict['name'] = f'{data["family_name"]}, {data["given_name"]}'
            json_dict['givenName'] = data['given_name']
            json_dict['familyName'] = data['family_name']

        if data.get('orcid'):
            json_dict['nameIdentifiers'].append({
                'nameIdentifier': data.get('orcid'),
                'nameIdentifierScheme': 'ORCID'
            })
        if data.get('researcher_id'):
            json_dict['nameIdentifiers'].append({
                'nameIdentifier': data.get('researcher_id'),
                'nameIdentifierScheme': 'ResearcherID'
            })
        return json_dict

    @classmethod
    def cite_schema_to_dict(cls, cite_schema_dict):
        is_not_person = 'givenName' not in cite_schema_dict
        if is_not_person:
            family_name = cite_schema_dict['name']
            given_name = None
        else:
            family_name = cite_schema_dict['familyName']
            given_name = cite_schema_dict['givenName']

        if 'affiliation' in cite_schema_dict:
            affiliation = cite_schema_dict['affiliation'][0]['name']
            affiliation_id = cite_schema_dict['affiliation'][0].get('affiliationIdentifier', 'https://ror.org/')
            affiliation_id = affiliation_id.split('ror.org/')[-1]  # Getting the last part should work whether it is N/A or an ror.org URL
        else:
            affiliation = None
            affiliation_id = None
        orcid = None
        researcher_id = None

        for identifier in cite_schema_dict.get('nameIdentifiers', []):
            if identifier['nameIdentifierScheme'] == 'ORCID':
                orcid = identifier['nameIdentifier']
            elif identifier['nameIdentifierScheme'] == 'ResearcherID':
                researcher_id = identifier['nameIdentifier']

        form_dict = {
            'family_name': family_name,
            'given_name': given_name,
            'affiliation': affiliation,
            'affiliation_id': affiliation_id,
            'is_not_person': is_not_person
        }

        if orcid:
            form_dict['orcid'] = orcid
        if researcher_id:
            form_dict['researcher_id'] = researcher_id

        return form_dict

    def clean(self):
        cleaned_data = super().clean()
        # This is super-hacky, but checkboxes are weird. Apparently, if they are not checked, they don't POST anything.
        # But since this is a required field, Django sends back an error. Since errors are added during cleaning,
        # we have to both set a default value of False *and* remove the error it created.
        cleaned_data.setdefault('is_not_person', False)
        self.errors.pop('is_not_person', None)

        affil = cleaned_data.get('affiliation', '')
        affil_id = cleaned_data.get('affiliation_id', '')
        # Now check the affiliation ID. If *either* an affiliation is provided or this is an institution of some sort,
        # there must be an affiliation ID. If it's not N/A, we check it against ror.org.
        if cleaned_data['is_not_person'] or affil:
            if not affil_id:
                self.add_error('affiliation_id', 'Required if "Institution/group" checked or affiliation provided. Use N/A if no affiliation ID exists.')
            elif affil_id.lower() not in {'na', 'n/a'}:
                r = requests.get(f'https://api.ror.org/organizations/{affil_id}')
                if not r.ok:
                    self.add_error('affiliation_id', 'Could not find this ID on ror.org.')
            else:
                cleaned_data['affiliation_id'] = 'N/A'  # ensure a standard value
        return cleaned_data


class ContributorForm(CreatorForm):
    # A contributor has most of the same fields as a creator, with one extra: a type
    # Also given name and affiliation are not required

    affiliation = forms.CharField(
        label='Affiliation (optional)',
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter affiliation (e.g. institute, city, [state], country) here',
            'style': f'width:{_base_field_width}; height: 3rem;'
        })
    )

    TYPE_NONE = '-'
    TYPE_CONTACT_PERSON = 'ContactPerson'
    TYPE_DATA_COL = 'DataCollector'
    TYPE_DATA_CUR = 'DataCurator'
    TYPE_DATA_MAN = 'DataManager'
    TYPE_DIST = 'Distributor'
    TYPE_ED = 'Editor'
    TYPE_HOST_INST = 'HostingInstitution'
    TYPE_PROD = 'Producer'
    TYPE_PROJ_LEAD = 'ProjectLeader'
    TYPE_PROJ_MAN = 'ProjectManager'
    TYPE_PROJ_MEM = 'ProjectMember'
    TYPE_REG_AGCY = 'RegistrationAgency'
    TYPE_REG_AUTH = 'RegistrationAuthority'
    TYPE_REL_PERS = 'RelatedPerson'
    TYPE_RES = 'Researcher'
    TYPE_RES_GRP = 'ResearchGroup'
    TYPE_RIGHTS_HOLD = 'RightsHolder'

    # Need to set the initial value here so that the formset correctly identifies
    # if this has not changed. For the curious, the `full_clean` method of a Django
    # form will skip validation *if* the form is allowed to be empty *and* it has not
    # changed (django/forms/forms.py). `has_changed()` in turn calls `changed_data()`,
    # which compares the initial value to the current value. If `initial` is not provided,
    # the default is `None`. For text fields, that works - they will return `None` if
    # nothing was entered. For multiple choice fields, those *always* have something,
    # so we need to set the initial value to some other placeholder.
    contributor_type = forms.ChoiceField(initial='-', choices=[
        (TYPE_NONE, '-'),
        (TYPE_CONTACT_PERSON, 'Contact person'),
        (TYPE_DATA_COL, 'Data collector'),
        (TYPE_DATA_CUR, 'Data curator'),
        (TYPE_DATA_MAN, 'Data manager'),
        (TYPE_DIST, 'Distributor'),
        (TYPE_ED, 'Editor'),
        (TYPE_HOST_INST, 'Hosting institution'),
        (TYPE_PROD, 'Producer'),
        (TYPE_PROJ_LEAD, 'Project leader'),
        (TYPE_PROJ_MAN, 'Project manager'),
        (TYPE_PROJ_MEM, 'Project member'),
        (TYPE_REG_AGCY, 'Registration agency'),
        (TYPE_REG_AUTH, 'Registration authority'),
        (TYPE_REL_PERS, 'Related person'),
        (TYPE_RES, 'Researcher'),
        (TYPE_RES_GRP, 'Research group'),
        (TYPE_RIGHTS_HOLD, 'Rights holder')
    ])

    def clean_contributor_type(self):
        data = self.cleaned_data['contributor_type']
        if data == self.TYPE_NONE:
            raise forms.ValidationError('You must choose a contributor type', code='no_contrib_type')
        return data

    def to_dict(self):
        json_dict = super().to_dict()
        json_dict['contributorType'] = self.cleaned_data['contributor_type']
        return json_dict

    @classmethod
    def cite_schema_to_dict(cls, cite_schema_dict):
        form_dict = super().cite_schema_to_dict(cite_schema_dict)
        form_dict['contributor_type'] = cite_schema_dict['contributorType']
        return form_dict


class RelatedIdentifierForm(MetadataAbstractForm):
    REL_NONE = '-'
    REL_CITED_BY = 'IsCitedBy'
    REL_CITES = 'Cites'
    REL_SUPP_TO = 'IsSupplementTo'
    REL_SUPP_BY = 'IsSupplementedBy'
    REL_CONT_BY = 'IsContinuedBy'
    REL_CONTS = 'Continues'
    REL_HAS_META = 'HasMetadata'
    REL_IS_META_FOR = 'IsMetadataFor'
    REL_NEW_VER = 'IsNewVersionOf'
    REL_PREV_VER = 'IsPreviousVersionOf'
    REL_PART_OF = 'IsPartOf'
    REL_HAS_PART = 'HasPart'
    REL_REF_BY = 'IsReferencedBy'
    REL_REFS = 'References'
    REL_DOC_BY = 'IsDocumentedBy'
    REL_DOCS = 'Documents'
    REL_COMP_BY = 'IsCompiledBy'
    REL_VAR_OF = 'IsVariantFormOf'
    REL_ORIG_OF = 'IsOriginalFormOf'

    relation_type = forms.ChoiceField(
        initial='-',
        help_text='How the TCCON dataset relates to this resource you are adding, e.g. "TCCON data is cited by this article"',
        choices=[
            (REL_NONE, '-'),
            (REL_CITED_BY, 'Is cited by'),
            (REL_CITES, 'Cites'),
            (REL_SUPP_TO, 'Is supplement to'),
            (REL_SUPP_BY, 'Is supplemented by'),
            (REL_CONT_BY, 'Is continued by'),
            (REL_CONTS, 'Continues'),
            (REL_HAS_META, 'Has metadata'),
            (REL_IS_META_FOR, 'Is metadata for'),
            (REL_NEW_VER, 'Is new version of'),
            (REL_PREV_VER, 'Is previous version of'),
            (REL_PART_OF, 'Is part of'),
            (REL_HAS_PART, 'Has part'),
            (REL_REF_BY, 'Is referenced by'),
            (REL_REFS, 'References'),
            (REL_DOC_BY, 'Is documented by'),
            (REL_DOCS, 'Documents'),
            (REL_COMP_BY, 'Is compiled by'),
            (REL_VAR_OF, 'Is variant form of'),
            (REL_ORIG_OF, 'Is original form of')
        ]
    )

    TYPE_NONE = '-'
    TYPE_ARK = 'ARK'
    TYPE_ARXIV = 'arXiv'
    TYPE_BIBCODE = 'bibcode'
    TYPE_DOI = 'DOI'
    TYPE_EAN13 = 'EAN13'
    TYPE_EISSN = 'EISSN'
    TYPE_HANDLE = 'Handle'
    TYPE_IGSN = 'IGSN'
    TYPE_ISBN = 'ISBN'
    TYPE_ISSN = 'ISSN'
    TYPE_ISTC = 'ISTC'
    TYPE_LISSN = 'LISSN'
    TYPE_LISD = 'LISD'
    TYPE_PMID = 'PMID'
    TYPE_PURL = 'PURL'
    TYPE_UPC = 'UPC'
    TYPE_URL = 'URL'
    TYPE_URN = 'URN'

    related_identifier_type = forms.ChoiceField(initial='-', choices=[
        (TYPE_NONE, '-'),
        (TYPE_ARK, 'ARK'),
        (TYPE_ARXIV, 'arXiv'),
        (TYPE_BIBCODE, 'bibcode'),
        (TYPE_DOI, 'DOI'),
        (TYPE_EAN13, 'EAN13'),
        (TYPE_EISSN, 'EISSN'),
        (TYPE_HANDLE, 'Handle'),
        (TYPE_IGSN, 'IGSN'),
        (TYPE_ISBN, 'ISBN'),
        (TYPE_ISSN, 'ISSN'),
        (TYPE_ISTC, 'ISTC'),
        (TYPE_LISSN, 'LISSN'),
        (TYPE_LISD, 'LISD'),
        (TYPE_PMID, 'PMID'),
        (TYPE_PURL, 'PURL'),
        (TYPE_UPC, 'UPC'),
        (TYPE_URL, 'URL'),
        (TYPE_URN, 'URN')
    ])

    related_identifier = forms.CharField(
        label='Related identifier',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter the identifier here',
            'style': f'width:{_base_field_width};'
        })
    )

    def clean_relation_type(self):
        data = self.cleaned_data['relation_type']
        if data == self.REL_NONE:
            raise forms.ValidationError('You must choose a relation type', code='no_relation_type')
        return data

    def clean_id_type(self):
        data = self.cleaned_data['related_identifier_type']
        if data == self.TYPE_NONE:
            raise forms.ValidationError('You must choose a related identifier type', code='no_relation_type')
        return data

    def to_dict(self):
        data = self.cleaned_data
        json_dict = {
            'relatedIdentifier': data['related_identifier'],
            'relationType': data['relation_type'],
            'relatedIdentifierType': data['related_identifier_type'],
        }
        return json_dict

    @classmethod
    def cite_schema_to_dict(cls, cite_schema_dict):
        form_dict = {
            'related_identifier': cite_schema_dict['relatedIdentifier'],
            'relation_type': cite_schema_dict['relationType'],
            'related_identifier_type': cite_schema_dict['relatedIdentifierType']
        }

        return form_dict


class FundingReferenceForm(MetadataAbstractForm):
    FUND_NONE = '-'
    FUND_ISNI = 'ISNI'
    FUND_GRID = 'GRID'
    FUND_CROSSREF = 'Crossref Funder'
    FUND_OTHER = 'Other'

    funder_identifier_type = forms.ChoiceField(initial='-', choices=[
        (FUND_NONE, '-'),
        (FUND_ISNI, 'ISNI'),
        (FUND_GRID, 'GRID'),
        (FUND_CROSSREF, 'Crossref Funder'),
        (FUND_OTHER, 'Other')
    ])

    funder_name = forms.CharField(
        label='Funder name',
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter funder name here',
            'style': f'width:{_base_field_width};'
        })
    )

    funder_identifier = forms.CharField(
        label='Funder identifier (optional)',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter funder identifier (e.g. GRID or Crossref string) here',
            'style': f'width:{_base_field_width};'
        })
    )

    award_number = forms.CharField(
        label='Award number (optional)',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter award number here',
            'style': f'width:{_base_field_width};'
        })
    )

    award_uri = forms.CharField(
        label='Award URI (optional)',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter a link to a webpage about the award',
            'style': f'width:{_base_field_width};'
        })
    )

    award_title = forms.CharField(
        label='Award title (optional)',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter the formal name of the award',
            'style': f'width:{_base_field_width};'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        no_id_type = cleaned_data.get('funder_identifier_type', self.FUND_NONE) == self.FUND_NONE
        no_id = cleaned_data.get('funder_identifier', '') in (None, '')
        if no_id_type != no_id:
            raise forms.ValidationError('Must provide both or neither of the identifier and identifier type. '
                                        '(Make the type equal "-" if no identifier desired.', 'xor_id_and_type')

    def to_dict(self) -> dict:
        def n2s(v):
            return '' if v is None else v

        name = self.cleaned_data['funder_name']
        id_type = self.cleaned_data.get('funder_identifier_type', self.FUND_NONE)
        identifier = n2s(self.cleaned_data.get('funder_identifier', ''))
        number = n2s(self.cleaned_data.get('award_number', ''))
        uri = n2s(self.cleaned_data.get('award_uri', ''))
        title = n2s(self.cleaned_data.get('award_title', ''))

        json_dict = {'funderName': name}
        if id_type != self.FUND_NONE:
            json_dict['funderIdentifierType'] = id_type
        if identifier != '':
            json_dict['funderIdentifier'] = identifier
        if number != '':
            json_dict['awardNumber'] = number
        if uri != '':
            json_dict['awardURI'] = uri
        if title != '':
            json_dict['awardTitle'] = title

        return json_dict

    @classmethod
    def cite_schema_to_dict(cls, cite_schema_dict: dict) -> dict:
        return {
            'funder_name': cite_schema_dict['funderName'],
            'funder_identifier_type': cite_schema_dict.get('funderIdentifierType', '-'),
            'funder_identifier': cite_schema_dict.get('funderIdentifier', None),
            'award_number': cite_schema_dict.get('awardNumber', None),
            'award_uri': cite_schema_dict.get('awardURI', None),
            'award_title': cite_schema_dict.get('awardTitle', None)
        }


class MetadataBaseFormset(forms.BaseFormSet):
    cls_prefix = None
    cls_key = None
    cls_form = None

    def __init__(self, *args, prefix=None, **kwargs):
        if any(x is None for x in [self.cls_prefix, self.cls_key, self.cls_form]):
            raise TypeError(f'{self.__class__.__name__} is missing class information')

        if prefix is None:
            prefix = self.cls_prefix
        super().__init__(*args, prefix=prefix, **kwargs)

    @classmethod
    def cite_schema_to_list(cls, cite_schema_dict):
        element_list = cite_schema_dict.get(cls.cls_key, [])
        return [cls.cls_form.cite_schema_to_dict(el) for el in element_list]

    def to_list(self):
        elements = []
        for form in self:
            # I had to kludge this. In normal usage, Django recognizes when a form in a formset has not changed
            # and skips over its validation.
            if len(form.cleaned_data) > 0:
                elements.append(form.to_dict())
        return elements

    @classmethod
    def prettify_column_name(cls, colname):
        return colname


class CreatorBaseFormset(MetadataBaseFormset):
    cls_prefix = 'creatorsForm'
    cls_key = 'creators'
    cls_form = CreatorForm

    @classmethod
    def prettify_column_name(cls, colname):
        if colname.lower() == 'orcid':
            return 'ORCID'
        elif colname.lower() == 'is not person':
            return 'Institution'
        elif 'id' in colname:
            return re.sub(r'\bid\b', 'ID', colname)
        else:
            return colname


class ContributorBaseFormset(MetadataBaseFormset):
    cls_prefix = 'contributorsForm'
    cls_key = 'contributors'
    cls_form = ContributorForm

    @classmethod
    def prettify_column_name(cls, colname):
        if colname.lower() == 'orcid':
            return 'ORCID'
        elif colname.lower() == 'is not person':
            return 'Institution'
        elif 'id' in colname:
            return re.sub(r'\bid\b', 'ID', colname)
        else:
            return colname


class RelatedIdentifierBaseFormset(MetadataBaseFormset):
    cls_prefix = 'relatedIdForm'
    cls_key = 'relatedIdentifiers'
    cls_form = RelatedIdentifierForm


class FundingReferenceBaseFormset(MetadataBaseFormset):
    cls_prefix = 'fundingRefForm'
    cls_key = 'FundingReference'
    cls_form = FundingReferenceForm

    @classmethod
    def prettify_column_name(cls, colname):
        if 'uri' in colname:
            return re.sub(r'\suri', ' URI', colname)
        else:
            return colname


CreatorFormset = formset_factory(CreatorForm, formset=CreatorBaseFormset)
ContributorFormset = formset_factory(ContributorForm, formset=ContributorBaseFormset)
RelatedIdFormset = formset_factory(RelatedIdentifierForm, formset=RelatedIdentifierBaseFormset)
FundingReferenceFormset = formset_factory(FundingReferenceForm, formset=FundingReferenceBaseFormset)


class TypeRestrictedFileField(FileField):
    # Based on https://blog.bixly.com/accept-only-specific-file-types-in-django-file-upload
    def __init__(self, *args, **kwargs):
        self._content_types = set(kwargs.pop('content_types', {}))
        self._max_upload_bytes = kwargs.pop('max_upload_bytes', None)
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super().clean(*args, **kwargs)
        if data is None:
            return None

        file = data.file
        try:
            content_type = data.content_type
            file_size = file.seek(0, 2)  # seek to the end and get the byte position
            file.seek(0)  # then go back to the beginning
            if content_type not in self._content_types:
                raise forms.ValidationError('Unsupported file type "{}". Supported types are: {}'.format(
                    content_type, ', '.join(self._content_types)
                ))
            elif self._max_upload_bytes is not None and file_size > self._max_upload_bytes:
                raise forms.ValidationError('File exceeds allowed size of {} bytes (file size = {} bytes)'.format(
                    self._max_upload_bytes, file_size
                ))
        except AttributeError:
            pass

        return data


class ReleaseFlagUpdateForm(Form):
    start = forms.DateField(label='Start date', widget=forms.SelectDateWidget(years=tuple(range(2000, _this_year+1))))
    end = forms.DateField(label='End date', widget=forms.SelectDateWidget(years=tuple(range(2000, _this_year+1))))
    name = forms.ChoiceField(label='Flag reason', choices=_get_flag_name_choices)
    comment = forms.CharField(label='Comment', max_length=256)
    plot = TypeRestrictedFileField(label='Upload an image of a plot',
                                   required=False,
                                   max_upload_bytes=5*1024**2,  # 5 MB
                                   content_types=('image/jpg', 'image/jpeg', 'image/png'))

    def clean(self):
        cleaned_data = super().clean()
        print(cleaned_data)
        name = cleaned_data.get('name', None)
        flag_values = _get_flag_values()
        if name not in flag_values:
            # should never be the case, since the name has to be selected from a set of choices
            self.add_error('name', 'Error reason "{}" is not one of the allowed values'.format(name))

        if 'start' in cleaned_data and 'end' in cleaned_data and cleaned_data.get('start') > cleaned_data['end']:
            self.add_error('start', 'Start date cannot be after end date')
            self.add_error('end', 'End date cannot be before start date')

    def save_to_json(self, site_id, flag_id):
        curr_json = InfoFileLocks.read_json_file(settings.RELEASE_FLAGS_FILE)
        flag_defs = InfoFileLocks.read_json_file(settings.RELEASE_FLAGS_DEF_FILE)['definitions']

        # Update the JSON structure, add fields for the value and plot
        self.cleaned_data['value'] = flag_defs[self.cleaned_data['name']]
        if 'plot' in self.cleaned_data and self.cleaned_data['plot'] is not None:
            plot_data = self.cleaned_data['plot']
            _, ext = os.path.splitext(plot_data.name)
            plot_file = settings.FLAG_PLOT_DIRECTORY / '{}_{}_plot{}'.format(site_id, flag_id, ext)
            if not settings.FLAG_PLOT_DIRECTORY.exists():
                settings.FLAG_PLOT_DIRECTORY.mkdir()
            with open(plot_file, 'wb') as dest:
                for chunk in plot_data:
                    dest.write(chunk)
            self.cleaned_data['plot'] = str(plot_file.name)

        start = self.cleaned_data.pop('start')
        end = self.cleaned_data.pop('end')
        key = '{}_{}_{}_{}'.format(site_id, int(flag_id), start.strftime('%Y%m%d'), end.strftime('%Y%m%d'))
        curr_json[key] = self.cleaned_data
        self.update_flag_file(curr_json)

    @staticmethod
    def update_flag_file(flag_dict):
        utils.backup_file_rolling(settings.RELEASE_FLAGS_FILE)
        InfoFileLocks.write_json_file(settings.RELEASE_FLAGS_FILE, flag_dict, indent=4)
