#!/usr/bin/env python3
__doc__ = """mk_aws_ssh_config.py

Outputs an ssh client config file that can be Include'd in .ssh/config
The config consists of an entry for the bastion host and entries for
all instances with a Name tag. Instances connect through the bastion host.

Example:
  
  Config file foocorp-mgmnt.yml:
    ---
    aws_profile: foocorp
    instance_prefix: foocorp-
    bastion:
      host: 12.34.56.78
      user: alice
    instances:
      user: alice

  $ mk_aws_ssh_config foocorp-mgmnt.yml > $HOME/.ssh/foocorp_mgmnt_config

  The file will contain something like:

     Host foocorp-bastion
         Hostname 12.34.56.78
         User alice
     
     Host: foocorp-prd.alices-bobsledadventures.com
         Hostname 172.18.47.98
         User alice
         ProxyCommand ssh foocorp-bastion nc %h %p
     
     Host: foocorp-tst.alices-bobsledadventures.com
         Hostname 172.18.85.48
         User alice
         ProxyCommand ssh foocorp-bastion nc %h %p

  Now edit $HOME/.ssh/config and add the following line:

    Include foocorp_mgmnt_config

  Try it out:

  $ ssh foocorp-tst.alices-bobsledadventures.com
  alice@prd$ _
"""

import sys

import boto3
import yaml


def get_tag(instance, tagkey):
    for tag in instance["Tags"]:
        if tag["Key"] == tagkey:
            return tag["Value"]
    return None


try:
    cfgfilename = sys.argv[1]
except:
    sys.stderr.write(__doc__)
    sys.exit(1)

try:
    with open(cfgfilename, "r") as f:
        cfg = yaml.load(f)
except IOError:
    sys.stderr.write("Error reading file {}\n".format(cfgfilename))
    sys.exit(2)
except Exception as e:
    sys.stderr.write("YAML error:\n{}\n".format(e))
    sys.exit(2)

try:
    aws_profile = cfg["aws_profile"]
    instance_prefix = cfg.get("instance_prefix", "")
    bastion_host = cfg["bastion"]["host"]
    bastion_user = cfg["bastion"]["user"]
    instance_user = cfg["instances"]["user"]
except Exception as e:
    # I know this error handling sucks
    sys.stderr.write("Configuration error:\n{}\n".format(e))
    sys.exit(3)


bastion_config = """\
Host {}-bastion
    Hostname {}
    User {}

""".format(aws_profile, bastion_host, bastion_user)
configs = [bastion_config]


try:
    boto3.setup_default_session(profile_name=aws_profile)
    ec2 = boto3.client("ec2")
except Exception as e:
    sys.stderr.write("AWS Error: \n{}\n".format(e))
    sys.exit(4)

instances = ec2.describe_instances()["Reservations"][0]["Instances"]
for instance in instances:
    name = get_tag(instance, "Name")
    if name is None:
        continue

    configs.append("""\
Host: {}{}
    Hostname {}
    User {}
    ProxyCommand ssh {}-bastion nc %h %p

""".format(
        instance_prefix,
        name,
        instance["PrivateIpAddress"],
        instance_user,
        aws_profile))

sys.stdout.write("".join(configs))
