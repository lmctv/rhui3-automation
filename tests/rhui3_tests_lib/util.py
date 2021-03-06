""" Utility functions """


import os
import tempfile
import time
import random
import string
import yaml

from stitches.expect import Expect, ExpectFailed


class Util(object):
    '''
    Utility functions for instances
    '''
    @staticmethod
    def uncolorify(instr):
        """ Remove colorification """
        res = instr.replace("\x1b", "")
        res = res.replace("[91m", "")
        res = res.replace("[92m", "")
        res = res.replace("[93m", "")
        res = res.replace("[0m", "")
        return res

    @staticmethod
    def generate_gpg_key(connection, keytype="DSA", keysize="1024", keyvalid="0", realname="Key Owner", email="kowner@example.com", comment="comment"):
        '''
        Generate GPG keypair

        WARNING!!!
        It takes too long to wait for this operation to complete... use pre-created keys instead!
        '''
        Expect.enter(connection, "cat > /tmp/gpgkey << EOF")
        Expect.enter(connection, "Key-Type: " + keytype)
        Expect.enter(connection, "Key-Length: " + keysize)
        Expect.enter(connection, "Subkey-Type: ELG-E")
        Expect.enter(connection, "Subkey-Length: " + keysize)
        Expect.enter(connection, "Name-Real: " + realname)
        Expect.enter(connection, "Name-Comment: " + comment)
        Expect.enter(connection, "Name-Email: " + email)
        Expect.enter(connection, "Expire-Date: " + keyvalid)
        Expect.enter(connection, "%commit")
        Expect.enter(connection, "%echo done")
        Expect.enter(connection, "EOF")
        Expect.expect(connection, "root@")

        Expect.enter(connection, "gpg --gen-key --no-random-seed-file --batch /tmp/gpgkey")
        for _ in xrange(1, 200):
            Expect.enter(connection, ''.join(random.choice(string.ascii_lowercase) for x in range(200)))
            time.sleep(1)
            try:
                Expect.expect(connection, "gpg: done")
                break
            except ExpectFailed:
                continue

    @staticmethod
    def remove_amazon_rhui_conf_rpm(connection):
        '''
        Remove Amazon RHUI configuration rpm from instance (which owns /etc/yum/pluginconf.d/rhui-lb.conf file)
        '''
        Expect.enter(connection, "")
        Expect.expect(connection, "root@")
        Expect.enter(connection, "([ ! -f /etc/yum/pluginconf.d/rhui-lb.conf ] && echo SUCCESS ) || (rpm -e `rpm -qf --queryformat '%{NAME}\n' /etc/yum/pluginconf.d/rhui-lb.conf` && echo SUCCESS)")
        Expect.expect(connection, "[^ ]SUCCESS.*root@", 60)

    @staticmethod
    def remove_rpm(connection, rpmlist):
        '''
        Remove installed rpms from cli
        '''
        Expect.enter(connection, "")
        Expect.expect(connection, "root@")
        Expect.enter(connection, "rpm -e " + ' '.join(rpmlist) + " && echo SUCCESS")
        Expect.expect(connection, "[^ ]SUCCESS.*root@", 60)

    @staticmethod
    def install_pkg_from_rhua(rhua_connection, connection, pkgpath):
        '''
        Transfer package from RHUA host to the instance and install it
        @param pkgpath: path to package on RHUA node
        '''
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.close()
        rhua_connection.sftp.get(pkgpath, tfile.name)
        file_extension=os.path.splitext(pkgpath)[1]
        if file_extension == '.rpm':
            connection.sftp.put(tfile.name, tfile.name + file_extension)
            os.unlink(tfile.name)
            Expect.ping_pong(connection, "rpm -i " + tfile.name + file_extension + " && echo SUCCESS", "[^ ]SUCCESS", 60)
        else:
            connection.sftp.put(tfile.name, tfile.name + '.tar.gz')
            os.unlink(tfile.name)
            Expect.ping_pong(connection,  "tar -xzf" + tfile.name + ".tar.gz" + " && ./install.sh && echo SUCCESS", "[^ ]SUCCESS", 60)

    @staticmethod
    def get_initial_password(connection, pwdfile="/etc/rhui-installer/answers.yaml"):
        '''
        Read login password from file
        @param pwdfile: file with the password (defaults to /etc/rhui-installer/answers.yaml)
        '''
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.close()
        connection.sftp.get(pwdfile, tfile.name)
        with open(tfile.name, 'r') as filed:
            doc = yaml.load(filed)
            password = doc["rhua"]["rhui_manager_password"]
        if password[-1:] == '\n':
            password = password[:-1]
        return password

    @staticmethod
    def get_rpm_details(rpmpath):
        '''
        Get (name-version-release, name) pair for local rpm file
        '''
        if rpmpath:
            rpmnvr = os.popen("basename " + rpmpath).read()[:-1]
            rpmname = os.popen("rpm -qp --queryformat '%{NAME}\n' " + rpmpath + " 2>/dev/null").read()[:-1]
            return (rpmnvr, rpmname)
        else:
            return (None, None)

    @staticmethod
    def get_rhua_version(connection):
        '''
        get RHUA os version
        '''
        stdin, stdout, stderr = connection.exec_command('grep -E -o "[0-9]" /etc/redhat-release | head -1')
        for line in  stdout:
            return int(line)

    @staticmethod
    def wildcard(hostname):
        """ Hostname wildcard """
        hostname_particles = hostname.split('.')
        hostname_particles[0] = "*"
        return ".".join(hostname_particles)

