################################################################################
#Author: Tim Hendricks
#Purpose: Migrates data from Storage Gateway volumes to an S3 bucket by creating
#         a snapshot and then an instance with a volume created from the snapshot
#         when the upload command returns the instance is halted and terminated.
#Note: For security the access credentials are for the S3WriteOnlyUser, which can
# ONLY write to any s3 bucket, it cannot read or delete any objects.
################################################################################
#        
#!/usr/bin/python
import boto3
import time
ec2 = boto3.resource('ec2',region_name='')
sg = boto3.client('storagegateway',region_name='')
#create current snapshot
print "Creating snapshot"
snapshot = sg.create_snapshot(
        VolumeARN='',
        SnapshotDescription='Veeam Glacier migration temporary snapshot '+time.ctime())
snapshot=ec2.Snapshot(snapshot['SnapshotId'])
print "Snapshot process started, waiting to complete"
snapshot.wait_until_completed()
print "Snapshot completed, creating instance"
instance = ec2.create_instances(
        ImageId='ami-1ecae776', #Amazon linux with built in aws command line tools and NTFS read support
        MinCount=1,
        MaxCount=1,
        KeyName='',
        SecurityGroups=['default'],
        InstanceType='t2.micro',
        InstanceInitiatedShutdownBehavior='terminate',
        BlockDeviceMappings=[
               {
                       'VirtualName':'ephemeral3',
                       'DeviceName':'xvdz',
                       'Ebs':{
                               'SnapshotId':snapshot.snapshot_id,
                               'DeleteOnTermination':True,
                               'VolumeType':'standard'
                       },
               },
        ],
#UserData is a base64 encoded string that is passed to the instance and run as root.
#it is only ever run at instance creation
        UserData="""#!/bin/bash
        mkdir ~/.aws/
        echo "[default]
aws_access_key_id = ""
aws_secret_access_key = "" > ~/.aws/credentials
 
        echo "[default]
output = text
region = " > ~/.aws/config
                                     
        mkdir /awsgw
        mount -t ntfs /dev/xvdz2 /awsgw/
        aws s3 cp /awsgw/success.txt s3://<bucket-name>/success.txt
        cd /awsgw/"AWS Storage Gateway Encrypted_1"
        name=$(ls -tr *.vbm| tail -n 1)
        aws s3 cp "$name" s3://<bucket-name>/"$name"
        halt
        """
)
 
instance=instance[0]
print "Instance {0} created".format(instance.id)
instance.wait_until_exists()
print "Instance {0} now exists".format(instance.id)
instance.wait_until_running()
print "Instance {0} is now running".format(instance.id)
instance.wait_until_stopped()
print "Instance {0} has stopped".format(instance.id)
instance.wait_until_terminated()
print "Instance {0} has been terminated".format(instance.id)
