class NotificationManager {
  constructor(notifications) {
    this.notifications = notifications;
    this.container = document.querySelector('#nav_list');
    this.toggle_btn = document.querySelector('#navbarDropdownNotification')
    this.toggle_btn.addEventListener('hide.bs.dropdown', this.hide_dropdown.bind(this))
    this.updateHTML();
  }

  hide_dropdown(event){
    this.notifications = []
    //TODO send a signal to the server to mark notifications as read.
    this.updateHTML();
  }

  addNotification(notification) {
    this.notifications.unshift(notification);

    if (this.notifications.length > 20) {
      this.notifications.pop();
    }

    this.updateHTML();
    this.displayBrowserNotification(notification);
    this.updateDropdownVisibility();
    this.updateDropdownIndicator();
  }

  updateHTML() {
    this.container.innerHTML = '';

    if (this.notifications.length > 0) {
      if (!this.toggle_btn.classList.contains("notification-indicator")) {
          this.toggle_btn.classList.add("notification-indicator");
        }
      const unreadSection = document.createElement('div');
      unreadSection.className = 'list-group-title border-bottom';
      unreadSection.textContent = 'New';
      this.container.appendChild(unreadSection);
      this.notifications.forEach(notification => {
        const item = this.createNotificationItem(notification);
        unreadSection.insertAdjacentHTML('afterend', item);
      });
    } else {
        if (this.toggle_btn.classList.contains("notification-indicator")) {
              this.toggle_btn.classList.remove("notification-indicator");
        }
        const unreadSection = document.createElement('div');
      unreadSection.className = 'list-group-title border-bottom';
      unreadSection.textContent = 'No new notifications';
      this.container.appendChild(unreadSection);
    }
  }

  createNotificationItem(notification) {
    const { title, message, time } = notification;
    const item = `
      <div class="list-group-item">
        <a class="notification notification-flush ${notification.read ? '' : 'notification-unread'}" href="#!">
          <div class="notification-body">
            <p class="mb-1"><strong>${title}</strong> ${message}</p>
            <span class="notification-time">${time}</span>
          </div>
        </a>
      </div>
    `;
    return item;
  }

  handleSocketMessage(data) {
    if (data.type === 'notification') {
      this.addNotification(data);
    }
  }

  displayBrowserNotification(notification) {
    if (!("Notification" in window)) {
      // Browser doesn't support notifications
      return;
    }

    if (Notification.permission === "granted") {
      this.showNotification(notification);
    } else if (Notification.permission !== "denied") {
      Notification.requestPermission().then(permission => {
        if (permission === "granted") {
          this.showNotification(notification);
        }
      });
    }
  }

  showNotification(notification) {
    const { title, message } = notification;
    const options = {
      body: message
    };

    const notificationInstance = new Notification(title, options);

    notificationInstance.onclick = () => {
      // Handle notification click event, if needed
    };
  }

  updateDropdownVisibility() {
    const dropdown = document.querySelector('.dropdown-menu');
    if (dropdown.classList.contains('show')) {
      dropdown.classList.remove('show');
    } else {
      dropdown.innerHTML = '';
      this.updateHTML();
      dropdown.classList.add('show');
    }
  }

  updateDropdownIndicator() {
    const indicator = document.getElementById('navbarDropdownNotification');
    indicator.classList.toggle('notification-indicator', this.notifications.some(notification => !notification.read));
  }
}