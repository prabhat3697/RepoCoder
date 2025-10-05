# ShibuDB Setup Guide for RepoCoder

This guide helps you set up [ShibuDB](https://shibudb.org/) for persistent indexing in RepoCoder.

## What is ShibuDB?

ShibuDB is a next-generation database system with advanced vector search capabilities. It provides:
- **Vector Search**: Advanced similarity search for embeddings (replaces FAISS)
- **Multi-Space Architecture**: Organize data into separate spaces
- **High Performance**: Optimized storage with B-tree indexing
- **Cross-Platform**: Support for Linux and macOS
- **Persistent Storage**: No need to rebuild indexes on restart

## Installation

### Step 1: Download ShibuDB

Visit [https://shibudb.org/](https://shibudb.org/) and download the appropriate version for your system:

#### macOS
- **Apple Silicon**: Download the DMG, PKG, or TAR.GZ file
- **Intel**: Download the AMD64 version

#### Linux
- **Debian/Ubuntu**: Download the appropriate AMD64 or ARM64 package
- **RHEL/CentOS**: Download the appropriate AMD64 or ARM64 package

### Step 2: Install ShibuDB

#### macOS
```bash
# Using DMG (recommended)
# 1. Download and mount the DMG
# 2. Drag ShibuDB to Applications folder
# 3. Add to PATH (optional)

# Using PKG
sudo installer -pkg ShibuDB-1.0.2.pkg -target /

# Using TAR.GZ
tar -xzf ShibuDB-1.0.2.tar.gz
sudo cp shibudb /usr/local/bin/
```

#### Linux (Debian/Ubuntu)
```bash
# Install the package
sudo dpkg -i shibudb_1.0.2_amd64.deb

# Or for ARM64
sudo dpkg -i shibudb_1.0.2_arm64.deb
```

#### Linux (RHEL/CentOS)
```bash
# Install the package
sudo rpm -i shibudb-1.0.2-1.x86_64.rpm

# Or for ARM64
sudo rpm -i shibudb-1.0.2-1.aarch64.rpm
```

### Step 3: Start ShibuDB Server

```bash
# Start ShibuDB server on port 4444 (requires sudo)
sudo shibudb start 4444
```

The server will start and listen on `localhost:4444`.

### Step 4: Install Python Client

```bash
# Install the ShibuDB Python client
pip install shibudb-client>=1.0.1
```

## Configuration

### Default Settings

RepoCoder uses these default ShibuDB settings:
- **Host**: `localhost`
- **Port**: `4444`
- **Username**: `admin`
- **Password**: `admin`

### Custom Configuration

You can customize ShibuDB settings when starting RepoCoder:

```bash
python app.py --repo /path/to/your/repo \
  --shibudb-host localhost \
  --shibudb-port 4444 \
  --use-persistent-index
```

## Usage

### First Run (Full Index)

On the first run, RepoCoder will create a full index:

```bash
python app.py --repo /path/to/your/repo --use-persistent-index
```

This will:
1. Connect to ShibuDB
2. Create vector and metadata spaces
3. Index all files in your repository
4. Store embeddings and metadata persistently

### Subsequent Runs (Incremental Updates)

On subsequent runs, RepoCoder will only index changed files:

```bash
python app.py --repo /path/to/your/repo --use-persistent-index
```

This will:
1. Connect to ShibuDB
2. Load existing metadata
3. Compare current files with stored metadata
4. Only index new, modified, or deleted files
5. Update the persistent index

### Force Rebuild

To force a complete rebuild of the index:

```bash
python app.py --repo /path/to/your/repo --use-persistent-index --force-rebuild
```

## Benefits

### Performance Improvements

- **Faster Startup**: Only processes changed files
- **Persistent Storage**: No need to re-index on every restart
- **Efficient Updates**: Only updates what's changed

### Example Performance

| Scenario | Without ShibuDB | With ShibuDB |
|----------|----------------|--------------|
| First Run | 30 seconds | 30 seconds |
| No Changes | 30 seconds | 2 seconds |
| 1 File Changed | 30 seconds | 5 seconds |
| 10 Files Changed | 30 seconds | 15 seconds |

## API Endpoints

### Get Index Statistics

```bash
curl http://localhost:8000/stats
```

Response:
```json
{
  "total_files": 150,
  "total_chunks": 1200,
  "repo_root": "/path/to/your/repo",
  "space_name": "repocoder_a1b2c3d4",
  "shibudb_connected": true
}
```

### Force Reindex

```bash
curl -X POST http://localhost:8000/index \
  -H 'Content-Type: application/json' \
  -d '{"folder": "/path/to/your/repo"}'
```

## Troubleshooting

### Common Issues

#### 1. ShibuDB Connection Failed
```
Error: Failed to connect to ShibuDB
```

**Solutions**:
- Ensure ShibuDB server is running: `sudo shibudb start 4444`
- Check if port 4444 is available: `netstat -an | grep 4444`
- Verify firewall settings

#### 2. Permission Denied
```
Error: Permission denied when starting ShibuDB
```

**Solutions**:
- Use `sudo` to start ShibuDB: `sudo shibudb start 4444`
- Check file permissions on ShibuDB binary

#### 3. Port Already in Use
```
Error: Port 4444 is already in use
```

**Solutions**:
- Use a different port: `sudo shibudb start 4445`
- Update RepoCoder config: `--shibudb-port 4445`
- Kill existing process: `sudo pkill shibudb`

#### 4. Fallback to In-Memory Indexing
```
Warning: Falling back to in-memory indexing
```

**Solutions**:
- Check ShibuDB server status
- Verify network connectivity
- Check ShibuDB logs

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
export SHIBUDB_DEBUG=1
python app.py --repo /path/to/your/repo --use-persistent-index
```

## Advanced Configuration

### Custom ShibuDB Settings

You can customize ShibuDB behavior by modifying the `PersistentRepoIndexer` class:

```python
# In persistent_indexer.py
indexer = PersistentRepoIndexer(
    repo_root=repo_root,
    embed_model_name=embed_model,
    max_chunk_chars=1600,
    overlap=200,
    shibudb_host="your-shibudb-host",
    shibudb_port=4444
)
```

### Multiple Repositories

Each repository gets its own ShibuDB space:
- Space name format: `repocoder_{hash}`
- Hash is based on repository path
- Multiple repositories can use the same ShibuDB instance

### Backup and Restore

ShibuDB data is stored in the system data directory. To backup:

```bash
# Find ShibuDB data directory
sudo find / -name "shibudb" -type d 2>/dev/null

# Backup the data directory
sudo cp -r /path/to/shibudb/data /backup/location/
```

## Performance Tuning

### Vector Index Configuration

The persistent indexer uses these default settings:
- **Index Type**: HNSW (Hierarchical Navigable Small World)
- **Metric**: InnerProduct (for normalized embeddings)
- **Dimension**: Auto-detected from embedding model
- **Space Usage**: Single vector space for both vectors and metadata

### Memory Usage

ShibuDB uses additional memory for:
- Vector storage
- Index structures
- Metadata caching

Typical memory usage:
- **Small repo** (< 1000 files): +50-100MB
- **Medium repo** (1000-10000 files): +200-500MB
- **Large repo** (> 10000 files): +500MB-2GB

## Security Considerations

### Default Credentials

ShibuDB uses default credentials:
- **Username**: `admin`
- **Password**: `admin`

**Important**: Change these in production environments!

### Network Security

- ShibuDB listens on all interfaces by default
- Consider firewall rules for production
- Use VPN or private networks for remote access

## Support

### ShibuDB Documentation

- **Official Site**: [https://shibudb.org/](https://shibudb.org/)
- **Python Client**: [https://pypi.org/project/shibudb-client/](https://pypi.org/project/shibudb-client/)

### RepoCoder Issues

For RepoCoder-specific issues:
1. Check the logs for error messages
2. Verify ShibuDB server status
3. Test with `--force-rebuild` flag
4. Try without persistent indexing to isolate issues

This setup will significantly improve RepoCoder's performance by avoiding unnecessary re-indexing on every startup!
