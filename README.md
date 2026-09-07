# starter-home

## Installation

1. Clone this repository:

```
git clone https://github.com/isikkema/starter-home.git
```

2. Move into the starter-home directory:

```
cd starter-home
```

3. Run the install script:

```
./install.sh
```

4. Log out and log back in OR run:

```
source ~/.local/bin/env
```

and

```
newgrp incus
```

> [!NOTE]
> Until you log out and log back in, you'll need to run the above command every time your shell restarts.

5. Define your services.  
   Look at [Defining Services](#defining-services) for information on how to do this.

6. Setup starter-home.

```
starter-home setup
```

6. Deploy your server!

```
starter-home deploy
```

---

> [!NOTE]
> After your server is up and running, consider creating your own git repo and pushing this directory there. Include everything EXCEPT for the `local_backup.env` and `remote_backend.env` files, the secrets directory, and any files that contain any secret information in your defined services.

## Defining Services

Services are defined by creating [quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) files in a subdirectory of the `services/` directory.

Examples of service definitions can be found in [examples/](examples/).

## Backups

starter-home backups are handled by [restic](https://restic.readthedocs.io/en/stable/010_introduction.html) from inside the server.
They are encrypted with a user-defined password, and can be stored locally and/or remotely.

### Local Backups

By default, starter-home backs up to `host-storage/backup/`. This location along with the backup password is specified in `backup/local_backup.env`, which is generated during `starter-home setup`.

When deploying for the first time, starter-home will automatically restore from a local backup if it exists and `backup/local_backup.env` is defined.

### Remote Backups

You can also make starter-home automatically back up to a remote location. This is highly recommended.

To do this, create `backup/remote_backup.env` with the necessary environment variables defined for restic to locate and authenticate with the remote backup location.

A list of restic's supported environment variables can be found [here](https://restic.readthedocs.io/en/stable/075_scripting.html#environment-variables).  
Guides for setting up restic repositories can be found [here](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html).

When deploying for the first time, starter-home will automatically restore from a remote backup if a local backup does not exist and `backup/remote_backup.env` is defined.
