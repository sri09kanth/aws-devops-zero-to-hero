import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')

    # Get all EBS snapshots
    response = ec2.describe_snapshots(OwnerIds=['self'])

    # Set your retention policy here (e.g., retain snapshots for 7 days)
    retention_days = 7

    # Get all active EC2 instance IDs
    instances_response = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    active_instance_ids = set()

    for reservation in instances_response['Reservations']:
        for instance in reservation['Instances']:
            active_instance_ids.add(instance['InstanceId'])

    # Iterate through each snapshot and delete if it's not attached to any volume or the volume is not attached to a running instance
    for snapshot in response['Snapshots']:
        snapshot_id = snapshot['SnapshotId']
        volume_id = snapshot.get('VolumeId')

        # Check if the snapshot is older than the retention period
        snapshot_age = (context.aws_request_time.timestamp() - snapshot['StartTime'].timestamp()) / (60 * 60 * 24)



        if snapshot_age > retention_days:
            if not volume_id:
                # Delete the snapshot if it's not attached to any volume
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                sns.publish(
                    TopicArn='YOUR_SNS_TOPIC_ARN',
                    Message=f"Deleted EBS snapshot {snapshot_id} as it was not attached to any volume and exceeded the retention period."
                )
            else:
                # Check if the volume still exists
                try:
                    volume_response = ec2.describe_volumes(VolumeIds=[volume_id])
                    if not volume_response['Volumes'][0]['Attachments']:
                        ec2.delete_snapshot(SnapshotId=snapshot_id)
                        sns.publish(
                            TopicArn='YOUR_SNS_TOPIC_ARN',
                            Message=f"Deleted EBS snapshot {snapshot_id} as it was taken from a volume not attached to any running instance and exceeded the retention period."
                        )

                except ec2.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'InvalidVolume.NotFound':
                        # The volume associated with the snapshot is not found (it might have been deleted)
                        ec2.delete_snapshot(SnapshotId=snapshot_id)
                        sns.publish(
                            TopicArn='YOUR_SNS_TOPIC_ARN',
                            Message=f"Deleted EBS snapshot {snapshot_id} as its associated volume was not found and exceeded the retention period."
                        )                       
        # if not volume_id:
        #     # Delete the snapshot if it's not attached to any volume
        #     ec2.delete_snapshot(SnapshotId=snapshot_id)
        #     print(f"Deleted EBS snapshot {snapshot_id} as it was not attached to any volume.")
        # else:
        #     # Check if the volume still exists
        #     try:
        #         volume_response = ec2.describe_volumes(VolumeIds=[volume_id])
        #         if not volume_response['Volumes'][0]['Attachments']:
        #             ec2.delete_snapshot(SnapshotId=snapshot_id)
        #             print(f"Deleted EBS snapshot {snapshot_id} as it was taken from a volume not attached to any running instance.")
        #     except ec2.exceptions.ClientError as e:
        #         if e.response['Error']['Code'] == 'InvalidVolume.NotFound':
        #             # The volume associated with the snapshot is not found (it might have been deleted)
        #             ec2.delete_snapshot(SnapshotId=snapshot_id)
        #             print(f"Deleted EBS snapshot {snapshot_id} as its associated volume was not found.")
