// منطق القائمة الجانبية للجوال - Lona Panel

function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (!sidebar) return;
    
    // إنشاء الـ Overlay إذا لم يكن موجوداً
    let overlayElem = document.getElementById('sidebarOverlay');
    if (!overlayElem) {
        overlayElem = document.createElement('div');
        overlayElem.id = 'sidebarOverlay';
        overlayElem.className = 'sidebar-overlay';
        overlayElem.onclick = toggleMobileSidebar;
        document.body.appendChild(overlayElem);
    }

    sidebar.classList.toggle('active');
    overlayElem.classList.toggle('active');
    
    // منع التمرير في الخلفية عند فتح القائمة
    if(sidebar.classList.contains('active')) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = 'auto';
    }
}

// دالة لتصغير القائمة في وضع الديسكتوب
function toggleSidebar() {
    document.body.classList.toggle('collapsed-mode');
    if(document.body.classList.contains('collapsed-mode')) {
        localStorage.setItem('sidebarState', 'collapsed');
    } else {
        localStorage.setItem('sidebarState', 'expanded');
    }
}

// تطبيق حالة القائمة عند التحميل
document.addEventListener('DOMContentLoaded', function() {
    if(localStorage.getItem('sidebarState') === 'collapsed') {
        document.body.classList.add('collapsed-mode');
    }
});
