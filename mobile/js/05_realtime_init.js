// ----------------------------------------------------
// Realtime Subscription
// ----------------------------------------------------
function setupRealtime() {
    const supabaseClient = window.nexusSupabase;
    if (!supabaseClient) return;
    supabaseClient.channel('custom-all-channel')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'nexus_user' },
      (payload) => {
          backgroundSync();
      }
    ).on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'tasks' },
      (payload) => { backgroundSync(); }
    ).on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'habits' },
      (payload) => { backgroundSync(); }
    )
    .subscribe();
}

// App Initialization


// ================================================================
