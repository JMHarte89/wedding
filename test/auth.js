(function () {
  var path = window.location.pathname || '';
  var isLogin = path.indexOf('login.html') !== -1;
  if (isLogin) return;

  var role = localStorage.getItem('wedding_role');
  var isAdminPage = path.indexOf('admin.html') !== -1;

  if (isAdminPage && role !== 'admin') {
    window.location.replace('login.html?need=admin');
    return;
  }
  if (!role) {
    window.location.replace('login.html');
  }
})();
