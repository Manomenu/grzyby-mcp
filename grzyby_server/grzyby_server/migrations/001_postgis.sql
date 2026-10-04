-- PostGIS: forest stands are polygons, and "stands within X km" or "stands outside a national
-- park" are spatial queries. On the cluster the extension is created by CloudNativePG (the
-- Database resource in the platform repo), because the app's role is not a superuser; there
-- this line finds it already in place. Locally and in CI the role owns the server and creates it.
CREATE EXTENSION IF NOT EXISTS postgis;
