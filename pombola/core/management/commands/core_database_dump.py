import os
from os.path import dirname, join, realpath
import subprocess
import sys
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):

    help = 'Output a database dump only containing public data'
    args = '<OUTPUT-FILENAME>'

    def handle(self, *args, **options):
        if len(args) != 1:
            self.print_help(sys.argv[0], sys.argv[1])
            sys.exit(1)
        output_filename = args[0]
        tables = connection.introspection.table_names()
        tables_to_ignore = set([
            'auth_group',
            'auth_group_permissions',
            'auth_message',
            'auth_permission',
            'auth_user',
            'auth_user_groups',
            'auth_user_user_permissions',
            'django_admin_log',
            'django_select2_keymap',
            'django_session',
            'experiments_event',
            'feedback_feedback',
            'popit_resolver_entityname',
            'thumbnail_kvstore',
            # Older tables that might still be present:
            'comments2_comment',
            'comments2_commentflag',
            'django_comment_flags',
            'django_comments',
            'mz_comments_commentwithtitle',
            'votematch_submission',
            # Exclude PostGIS tables
            'layer',
            'topology',
        ])
        if settings.COUNTRY_APP in ('nigeria',):
            # In the past I think the hansard application was in use
            # for Nigeria, so these tables are present (and contain
            # data), but the hansard app is no longer used for
            # Nigeria.  So, it's best to ignore these tables to make
            # the dump smaller.  place_data and projects are similarly
            # no longer used (but those applications' tables are empty
            # anyway)
            tables_to_ignore.update([
                'hansard_alias',
                'hansard_entry',
                'hansard_sitting',
                'hansard_source',
                'hansard_venue',
                'place_data_entry',
                'projects_project',
            ])
        if settings.COUNTRY_APP in ('ghana',):
            # These tables are no longer used, I believe, and migrated
            # to core / hansard:
            tables_to_ignore.update([
                'ghana_hansardentry',
                'ghana_mp',
                'ghana_uploadmodel',
                'odekro_hansardentry',
                'odekro_mp',
                'odekro_uploadmodel'
            ])
        tables_to_dump = [
            t for t in tables if t not in tables_to_ignore
        ]
        expected_tables = [
            'budgets_budget',
            'budgets_budgetsession',
            'core_alternativepersonname',
            'core_contact',
            'core_contactkind',
            'core_identifier',
            'core_informationsource',
            'core_organisation',
            'core_organisationkind',
            'core_organisationrelationship',
            'core_organisationrelationshipkind',
            'core_parliamentarysession',
            'core_person',
            'core_place',
            'core_placekind',
            'core_position',
            'core_positiontitle',
            'core_slugredirect',
            'django_content_type',
            'django_migrations',
            'django_site',
            'experiments_experiment',
            'file_archive_file',
            'images_image',
            'info_category',
            'info_infopage',
            'info_infopage_categories',
            'info_infopage_tags',
            'info_tag',
            'info_viewcount',
            'instances_instance',
            'instances_instance_users',
            'mapit_area',
            'mapit_code',
            'mapit_codetype',
            'mapit_country',
            'mapit_generation',
            'mapit_geometry',
            'mapit_name',
            'mapit_nametype',
            'mapit_postcode',
            'mapit_postcode_areas',
            'mapit_type',
            'popit_apiinstance',
            'popit_person',
            'popolo_contactdetail',
            'popolo_identifier',
            'popolo_link',
            'popolo_membership',
            'popolo_organization',
            'popolo_othername',
            'popolo_person',
            'popolo_post',
            'popolo_source',
            'scorecards_category',
            'scorecards_entry',
            'slug_helpers_slugredirect',
            'south_migrationhistory',
            'tasks_task',
            'tasks_taskcategory',
        ]
        if settings.COUNTRY_APP in ('south_africa',):
            expected_tables += [
                'interests_register_category',
                'interests_register_entry',
                'interests_register_entrylineitem',
                'interests_register_release',
                'speeches_recording',
                'speeches_recordingtimestamp',
                'speeches_section',
                'speeches_slug',
                'speeches_speaker',
                'speeches_speech',
                'speeches_speech_tags',
                'speeches_tag',
                'za_hansard_answer',
                'za_hansard_pmgcommitteeappearance',
                'za_hansard_pmgcommitteereport',
                'za_hansard_question',
                'za_hansard_questionpaper',
                'za_hansard_source',
            ]
        if settings.COUNTRY_APP in ('nigeria', 'south_africa'):
            # spinner
            expected_tables += [
                'spinner_imagecontent',
                'spinner_quotecontent',
                'spinner_slide',
            ]
        if settings.COUNTRY_APP in ('ghana', 'kenya',):
            # hansard, place_data, projects, votematch, wordcloud
            expected_tables += [
                'hansard_alias',
                'hansard_entry',
                'hansard_sitting',
                'hansard_source',
                'hansard_venue',
                'place_data_entry',
                'projects_project',
                'votematch_answer',
                'votematch_party',
                'votematch_quiz',
                'votematch_stance',
                'votematch_statement',
            ]
        if settings.COUNTRY_APP in ('kenya',):
            # place_data, bills
            expected_tables += [
                'bills_bill',

            ]
        unexpected = set(tables_to_dump) - set(expected_tables)
        if unexpected:
            print '''The following tables were found which weren't expected
and which hadn't been explictly excluded.  If these are safe to make
available in a public database dump (in particular check that they
contain no personal information of site users) then add them to
'expected_table'. Otherwise (i.e. they should *not* be made availble
publicly) add them to 'tables_to_ignore'.'''
            for t in sorted(unexpected):
                print " ", t
            sys.exit(2)
        command = [
            'pg_dump',
            '--no-owner',
            '--no-acl',
        ]
        for t in tables_to_dump:
            command += ['-t', t]
        db_settings = connection.settings_dict
        if db_settings['HOST']:
            command += [
                '-h', db_settings['HOST'],
            ]
        if db_settings['USER']:
            command += [
                '-U', db_settings['USER'],
            ]
        command.append(db_settings['NAME'])
        if int(options['verbosity']) > 1:
            print >> sys.stderr, "Going to run the command:", ' '.join(command)
        output_directory = dirname(realpath(output_filename))

        ntf = NamedTemporaryFile(
            delete=False, prefix=join(output_directory, 'tmp')
        )
        with open(ntf.name, 'wb') as f:
            subprocess.check_call(command, stdout=f)
        os.chmod(ntf.name, 0o644)
        os.rename(ntf.name, output_filename)