// New visitors start with signup. Existing personnel can choose login directly.
// Both public screens are separate from access to protected workspace routes.
export function resolveRoute(requested = '', signedIn = false) {
  const route = String(requested ?? '').replace(/^#/, '');
  if (route === 'signup') return signedIn ? 'search' : 'signup';
  if (route === 'login') return 'login';
  if (!signedIn) return route ? 'login' : 'signup';
  if (route === 'actor' || route.startsWith('detail/')) return route;
  return 'search';
}
