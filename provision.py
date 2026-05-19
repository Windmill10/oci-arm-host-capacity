#!/usr/bin/env python3
import os
import sys
import time
import oci

config = {
    "user": os.environ["OCI_USER_ID"],
    "fingerprint": os.environ["OCI_KEY_FINGERPRINT"],
    "tenancy": os.environ["OCI_TENANCY_ID"],
    "region": os.environ["OCI_REGION"],
    "key_file": os.environ["OCI_PRIVATE_KEY_FILENAME"],
}

SHAPE = os.environ["OCI_SHAPE"]
OCPUS = float(os.environ["OCI_OCPUS"])
MEMORY = float(os.environ["OCI_MEMORY_IN_GBS"])
AD = os.environ["OCI_AVAILABILITY_DOMAIN"]
SUBNET_ID = os.environ["OCI_SUBNET_ID"]
IMAGE_ID = os.environ["OCI_IMAGE_ID"]
SSH_KEY = os.environ["OCI_SSH_PUBLIC_KEY"]
MAX_INSTANCES = int(os.environ.get("OCI_MAX_INSTANCES", "1"))
COMPARTMENT_ID = config["tenancy"]

compute = oci.core.ComputeClient(config)

# Check existing instances
instances = compute.list_instances(compartment_id=COMPARTMENT_ID).data
existing = [i for i in instances if i.shape == SHAPE and i.lifecycle_state not in ("TERMINATED", "TERMINATING")]
if len(existing) >= MAX_INSTANCES:
    names = ", ".join(i.display_name for i in existing)
    print(f"Already have {len(existing)} instance(s): {names}. Exiting.")
    sys.exit(0)

print(f"Found {len(existing)} existing {SHAPE} instance(s). Attempting to create...")

details = oci.core.models.LaunchInstanceDetails(
    compartment_id=COMPARTMENT_ID,
    availability_domain=AD,
    shape=SHAPE,
    shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=OCPUS, memory_in_gbs=MEMORY),
    source_details=oci.core.models.InstanceSourceViaImageDetails(image_id=IMAGE_ID),
    create_vnic_details=oci.core.models.CreateVnicDetails(
        subnet_id=SUBNET_ID,
        assign_public_ip=True,
    ),
    metadata={"ssh_authorized_keys": SSH_KEY},
    display_name=f"a1flex-{int(time.time())}",
)

try:
    resp = compute.launch_instance(details)
    print(f"SUCCESS: instance {resp.data.id} is {resp.data.lifecycle_state}")
    sys.exit(0)
except oci.exceptions.ServiceError as e:
    if e.status == 500 and "Out of host capacity" in e.message:
        print(f"Out of capacity in {AD} — will retry next run.")
        sys.exit(0)
    print(f"Unexpected error HTTP {e.status} {e.code}: {e.message}")
    sys.exit(2)
