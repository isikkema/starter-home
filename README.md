# starter-home

starter-home is an opinionated self-hosting platform that makes it easy to create and run a home server.

> Ok, but what does it do?

starter-home

- creates a server virtual machine (VM) using [Incus](https://linuxcontainers.org/incus/),
- configures it remotely using [Fabric](https://www.fabfile.org/)
    - (handling package installation, authentication, and networking),
- runs services inside the server VM in [Podman](https://docs.podman.io/en/latest/) containers
    - (which are defined by [Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) files),
- and handles backups for these services automatically using [restic](https://restic.net/).

> Ok, but what do _I_ need to do?

All you need to do is [install](#installation) starter-home and [define your services](#defining-services).

## Installation

starter-home is meant to be installed on a fresh Debian 13 installation. See [here](https://www.debian.org/download) for instructions on how to install Debian.

1. Clone this repository:

```
git clone https://github.com/isikkema/starter-home.git
```

This simply copies the files from GitHub to your computer.

2. Move into the starter-home directory:

```
cd starter-home
```

3. Run the install script:

```
./install.sh
```

This installs starter-home and its dependencies.

4. Log out and log back in OR run:

```
newgrp incus
```

This creates a new shell session where your user is part of the incus group.

> [!NOTE]
> Until you log out and log back in, you'll need to run the above command every time your shell restarts.

5. Setup starter-home.

```
starter-home setup
```

This command runs you through a one-time, guided setup where you can configure starter-home to your liking.

You'll be asked to configure specs for the starter-home VM, along with with some networking features like port forwarding and split DNS.

Yes or no questions will be denoted with `y/n: `. If one particular option is recommended, it will be capitalized, like so `Y/n: `, and selected by default if left blank.

Other configuration options will ask for generic open-ended input. In some cases, starter-home may recommend sensible defaults. In this case, those recommendations will be denoted in `[` square brackets `]`, like so `[8GiB]: `, and selected by default if left blank.

Look at the [The `starter-home setup` Command](#the-starter-home-setup-command) section of this README if you have questions about any of the setup options.

6. Define your services.

**This is the most important part.**

Your services are the programs you run on your server. They're the things you actually connect to and use.

Look at the [Defining Services](#defining-services) section of this README for information on how to do this.

Or if you're just looking to try out starter-home, feel free to copy some example services from `examples/` to the `services/` directory.
Ex: `cp -r examples/caddy/ examples/jellyfin/ services/`

7. Deploy your server!

```
starter-home deploy
```

This command is what you'll most often be using.

When you first run this, it will create the starter-home VM with an IP address of `10.50.0.100` and configure it to run the services you've defined.

On subsequent runs, it will apply any changes you've made to your service definitions. Updated services will be restarted, new services will be spun up, and deleted services will be stopped and removed.

8. Use your services!

Congrats! Your server is up and running.

You can reach your server at `10.50.0.100`. You can also reach your service at `10.50.0.100:<whatever_port_you_published>`.

If you let starter-home setup split DNS,

- And you told starter-home **NOT** to resolve `*.starter.home.arpa` to your host's LAN IP

  You can reach your service at `starter.home.arpa:<whatever_port_you_published>`.

- And you told starter-home to resolve `*.starter.home.arpa` to your host's LAN IP
  - And you forwarded a port from `<source_port>` to `<whatever_port_you_published>`

    You can reach your service at `starter.home.arpa:<source_port>`

    - And `<source_port>` is `80`
      - And your service is meant to be accessed through the web

        You can reach your service at `http://starter.home.arpa`

---

> [!NOTE]
> After your server is up and running, consider creating your own git repo and pushing this directory there. Include everything EXCEPT for the `local_backup.env` and `remote_backup.env` files, the secrets directory, and any files that contain any secret information in your defined services.

## The `starter-home setup` Command

After running `starter-home setup`, you'll be given several options for configuring your server.

The first set of options will ask about the physical computing resources that should be given to your server VM.

- Number of CPUs: This is the number of CPU processors that the VM will make available to the services and processes running inside of itself. You should choose a number smaller than the amount of CPUs available on the host so that the host can run the processes that it needs. If available, the recommended number is a good default.

- Memory: This is the amount of memory or RAM that will be allocated to the VM. As before, choose an amount smaller than is available on the host so that the host can run necessary processes.

- Disk Size: This is the amount of disk space that the VM will have. The proper amount will vary based on the use-case of the server and the services running. If you suspect the services you're running will need to store a lot of data inside the VM or inside volumes, choose a higher amount. Conversely, if you don't suspect the services you run will need to store that much data but you'll likely be storing lots of data on the host (either through outside processes or `host-storage/`), then choose a smaller number. As always, choose a number smaller than is available on the host so that the host can still create necessary files.

- Do you want to forward ports: This is a set of convenience options which allow starter-home to make it easier for you to access your services.

    - Host computer's LAN IP: This asks for your computer's IP address on your home's local network. starter-home uses this as the IP address to listen on for any source ports that are forwarded.

    - Forward Port: This asks for a single source port and single destination port, which is forwarded like so `<Host's LAN IP>:<source port> -> 10.50.0.100:<destination port>`, keeping in mind that `10.50.0.100` is the server VM's IP. It will continue to ask for more ports until you leave it blank and hit enter.

    - Password for local backups: This is the password that starter-home will use for the local restic repository at `host-storage/backup/`. A password is required for restic repositories. This password is saved in `backup/local_backup.env` for use by starter-home.

    - Do you want starter-home to automatically setup split DNS: This allows starter-home to automatically set things up on your host computer so that `*.starter.home.arpa` resolves to `10.50.0.100`. This allows you to access web services in your web browser by visiting `http://your_configured_service_name_here.starter.home.arpa:<your_service_port_here>`. Your configured service name and port will vary based on how you've defined your service.

    - Do you want to resolve *.starter.home.arpa to <Host's LAN IP>: This makes `*.starter.home.arpa` resolve to your host's LAN IP which you configured earlier rather than `10.50.0.100`. This is useful if you'd rather access your services through your forwarded ports. For example, say you have your Jellyfin service running on port 8096. You could forward port 80 to 8096 and then simply visit `http://jellyfin.starter.home.arpa` rather than having to specify 8096 as the port number.

- Does this look right: Finally, starter-home shows you a summary of your selected options. If you've changed your mind, just enter "n", and no changes will be made. Otherwise, enter "y" to confirm your choices and run the setup.

## Defining Services

Each service is defined in its own subdirectory inside `services/`.

Inside this subdirectory, you must create exactly one file named `<service>.container`. This file will define what the service is and how it is run.

You can then create any additional supporting files if necessary. These supporting files can end in `.volume`, `.network`, or `.build`.

Sometimes, services may need additional configuration or data that is handled by the service itself. In this case, create `resources/` and place those files there.

### Example

Suppose you wanted to run Jellyfin on your server.

- You'd start by creating a `jellyfin/` subdirectory in `services/`.

```
mkdir services/jellyfin/
```

- Then you'd create `services/jellyfin/jellyfin.container` with the following contents:

```
[Unit]
Description=Jellyfin media server # This can be anything. Write whatever you want here to describe your service.

[Container]
ContainerName=jellyfin
Image=docker.io/jellyfin/jellyfin:latest  # This is where the program actually comes from. It's very likely someone has already bundled the service you want to run in a container image like this.
PublishPort=8096:8096                 # This allows ports from inside the container to be accessible outside the container. In this case, port 8096 inside the container is accessible as port 8096 outside the container.
Network=web.network                   # This is the network that the service will run on. This is important if there are any other services you run that this service will need to be able to talk to.
Volume=jellyfin-config.volume:/config # These are volumes. In this case, the jellyfin-config volume is being mounted to the `/config` directory inside the service container. Any files that the service writes to the `/config` directory will be written to the jellyfin-config volume. Volumes are saved across service restarts and are included in all backups.
Volume=jellyfin-cache.volume:/cache
Volume=/host-storage/media:/media:ro  # In this case, `/host-storage/media` on the VM is mounted to `/media` on the container. And since `host-storage/` on the host is mounted to `/host-storage/` on the VM, that means `host-storage/media/` is actually stored on the host. The ro at the end means that the container can only read, and not write to `/media`. Since this isn't a volume, it isn't backed up. This is useful when you want to persist data across restarts and even different VMs, but don't want it to be included in backups.

[Service]
ExecStartPre=mkdir -p /host-storage/media # This creates `/host-storage/media/` on the VM before the service starts.
Restart=always                            # This restarts the service if it ever stops.

[Install]
WantedBy=default.target # This makes sure the service starts whenever the VM reboots.
```

- Then you'll want to create all the supporting files that `services/jellyfin/jellyfin.container` depends on.

`services/jellyfin/web.network`

```
[Network]
NetworkName=web
```

`services/jellyfin/jellyfin-config.volume`

```
[Volume]
VolumeName=jellyfin-config
```

`services/jellyfin/jellyfin-cache.volume`

```
[Volume]
VolumeName=jellyfin-cache
```

- That's it!

Run `starter-home deploy` to start your new service!

And access it at `http://10.50.0.100:8096`.

### More Examples

More examples of service definitions can be found in [examples/](examples/).

If you must know, these files I've been having you create are called quadlet files. All the available types, syntax, and options for quadlet files can be found [here](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html).

## Backups

starter-home backups are handled by [restic](https://restic.readthedocs.io/en/stable/010_introduction.html) from inside the server.
They are encrypted with a user-defined password, and can be stored locally and/or remotely.

Backups are automatically created every night at around 3am.

You can also manually create a backup whenever you want by running `starter-home backup create`.

### Local Backups

By default, starter-home backs up to `host-storage/backup/`. This location along with the backup password is specified in `backup/local_backup.env`, which is generated during `starter-home setup`.

When deploying for the first time, starter-home will automatically restore from the latest local backup if it exists and `backup/local_backup.env` is defined.

That means you can:

1. delete the entire server VM with `starter-home delete`.
2. run `starter-home deploy`.
3. continue using your services as they were when a backup was last created.

### Remote Backups

You can also make starter-home automatically back up to a remote location. This is highly recommended.

To do this, create `backup/remote_backup.env` with the necessary environment variables defined for restic to locate and authenticate with the remote backup location.

A list of restic's supported environment variables can be found [here](https://restic.readthedocs.io/en/stable/075_scripting.html#environment-variables).  
Guides for setting up restic repositories can be found [here](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html).

When deploying for the first time, starter-home will automatically restore from a remote backup if a local backup does not exist and `backup/remote_backup.env` is defined.

That means that you can:

1. manually create a remote backup.
2. copy your service definitions and `remote_backup.env` to a safe location.
3. throw your computer into a wood chipper **(required).**
4. install starter-home on a new computer.
5. copy your service definitions and `remote_backup.env` to the new computer.
6. run `starter-home deploy`.
7. continue using your services as they were on your formerly non-wood-chipped computer when a remote backup was last created.
