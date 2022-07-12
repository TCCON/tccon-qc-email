from argparse import ArgumentParser
import os
from .qc_email import send_email_from_config


def main():
    p = ArgumentParser(description='Send a QC email manually, or do a test')
    p.add_argument('--cfg-file', required=True, help='Path to the TOML configuration file')
    p.add_argument('--nc-file', required=True, help='The netCDF file')
    p.add_argument('-a', '--attachment', required=True, help='A PDF to attach')
    p.add_argument('--plot-url', help='The URL where these plots can be viewed')
    p.add_argument('--site-id', help='The two letter site ID (overrides the one from the netCDF file name)')
    p.add_argument('-s', '--not-dry-run', action='store_false', dest='dry_run', help='Actually send the email, do not do a dry run')

    clargs = p.parse_args()
    site_id = clargs.site_id if clargs.site_id is not None else os.path.basename(clargs.nc_file)[:2]
    send_email_from_config(
        cfg_file=clargs.cfg_file,
        site_id=site_id,
        attachment=clargs.attachment,
        nc_file=clargs.nc_file,
        plot_url=clargs.plot_url,
        dry_run=clargs.dry_run
    )

if __name__ == '__main__':
    main()
