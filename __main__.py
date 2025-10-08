import pulumi
import pulumi_aws as aws

config = pulumi.Config()
ssh_pub_key = config.require("sshPublicKey")

# VPC
vpc = aws.ec2.Vpc("pulumi-vpc",
    cidr_block="10.0.0.0/16",
    tags={"Name": "pulumi-vpc"}
)

# Public subnet
subnet = aws.ec2.Subnet("pulumi-public-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=True,
    tags={"Name": "pulumi-public-subnet"}
)

# Internet gateway + route table
igw = aws.ec2.InternetGateway("pulumi-igw", vpc_id=vpc.id)
route_table = aws.ec2.RouteTable("pulumi-public-rt",
    vpc_id=vpc.id,
    routes=[{"cidr_block": "0.0.0.0/0", "gateway_id": igw.id}],
    tags={"Name": "pulumi-public-rt"}
)
rt_assoc = aws.ec2.RouteTableAssociation("pulumi-rt-assoc",
    subnet_id=subnet.id,
    route_table_id=route_table.id
)

# Security group
sg = aws.ec2.SecurityGroup("pulumi-web-sg",
    vpc_id=vpc.id,
    description="Allow SSH and HTTP",
    ingress=[
        {"protocol": "tcp", "from_port": 22, "to_port": 22, "cidr_blocks": ["0.0.0.0/0"]},
        {"protocol": "tcp", "from_port": 80, "to_port": 80, "cidr_blocks": ["0.0.0.0/0"]}
    ],
    egress=[
        {"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}
    ],
    tags={"Name": "pulumi-web-sg"}
)

# Key pair from public key
keypair = aws.ec2.KeyPair("pulumi-deployer-key", public_key=ssh_pub_key)

# AMI (Amazon Linux 2)
ami = aws.ec2.get_ami(most_recent=True,
    owners=["amazon"],
    filters=[{"name": "name", "values": ["amzn2-ami-hvm-*-x86_64-gp2"]}]
)

# EC2 instance with a small web page
user_data = """#!/bin/bash
sudo yum update -y
sudo yum install -y httpd
sudo systemctl enable httpd
sudo systemctl start httpd
echo "Hello from Pulumi-created EC2" > /var/www/html/index.html
"""

server = aws.ec2.Instance("pulumi-web-server",
    instance_type="t2.micro",
    ami=ami.id,
    subnet_id=subnet.id,
    vpc_security_group_ids=[sg.id],
    key_name=keypair.key_name,
    associate_public_ip_address=True,
    user_data=user_data,
    tags={"Name": "pulumi-web-server"}
)

# Exports
pulumi.export("public_ip", server.public_ip)
pulumi.export("public_dns", server.public_dns)