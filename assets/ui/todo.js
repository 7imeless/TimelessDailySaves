(() => {
        const calendarPanel = document.querySelector('.calendar-panel');
        if (!calendarPanel) return;
        const scheduleNotice = (root) => {
          const notice = root.querySelector('[data-auto-hide="true"]');
          if (!notice) return;
          window.setTimeout(() => notice.classList.add('is-hiding'), 2600);
          window.setTimeout(() => notice.remove(), 3100);
        };
        const replaceTodo = (markup) => {
          const template = document.createElement('template');
          template.innerHTML = markup.trim();
          const nextTodo = template.content.querySelector('#todo');
          const currentTodo = document.getElementById('todo');
          if (!nextTodo || !currentTodo) throw new Error('Todo panel missing');
          currentTodo.replaceWith(nextTodo);
          scheduleNotice(nextTodo);
          return { template, nextTodo };
        };
        scheduleNotice(document);
        calendarPanel.addEventListener('click', async (event) => {
          const editLink = event.target.closest('.todo-actions a');
          if (editLink && calendarPanel.contains(editLink)) {
            event.preventDefault();
            try {
              const response = await fetch(editLink.href, { headers: { 'X-Requested-With': 'fetch' } });
              if (!response.ok) throw new Error('Todo edit failed');
              replaceTodo(await response.text());
            } catch (error) {
              window.location.assign(editLink.href);
            }
            return;
          }
          const link = event.target.closest('a.calendar-day, a.calendar-nav, a.todo-date-link');
          if (!link || !calendarPanel.contains(link)) return;
          event.preventDefault();
          const targetUrl = new URL(link.href, window.location.href);
          const dateValue = targetUrl.searchParams.get('todo_date');
          if (!dateValue) return;
          link.setAttribute('aria-busy', 'true');
          try {
            const isMonthNavigation = link.classList.contains('calendar-nav') || link.classList.contains('todo-date-link');
            const endpoint = isMonthNavigation
              ? `/calendar/view?month=${encodeURIComponent(targetUrl.searchParams.get('month') || '')}&todo_date=${encodeURIComponent(dateValue)}`
              : `/todo/view?date=${encodeURIComponent(dateValue)}`;
            const response = await fetch(endpoint, {
              headers: { 'X-Requested-With': 'fetch' }
            });
            if (!response.ok) throw new Error('Todo view failed');
            const { template } = replaceTodo(await response.text());
            if (isMonthNavigation) {
              const nextCalendar = template.content.querySelector('#calendar');
              const currentCalendar = document.getElementById('calendar');
              if (!nextCalendar || !currentCalendar) throw new Error('Calendar missing');
              currentCalendar.replaceWith(nextCalendar);
            } else {
              const currentCalendar = document.getElementById('calendar');
              currentCalendar.querySelectorAll('.calendar-day.is-selected').forEach((day) => day.classList.remove('is-selected'));
              link.classList.add('is-selected');
            }
            window.history.replaceState({}, '', `${targetUrl.pathname}${targetUrl.search}#todo`);
          } catch (error) {
            window.location.assign(link.href);
          } finally {
            link.removeAttribute('aria-busy');
          }
        });
        calendarPanel.addEventListener('submit', async (event) => {
          const form = event.target.closest('#todo form');
          if (!form || !calendarPanel.contains(form)) return;
          event.preventDefault();
          const submitter = event.submitter;
          if (submitter) submitter.disabled = true;
          try {
            const response = await fetch(form.action, {
              method: form.method || 'POST',
              body: new URLSearchParams(new FormData(form)),
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'X-Requested-With': 'fetch'
              }
            });
            const markup = await response.text();
            if (!markup.includes('id="todo"')) throw new Error('Todo update failed');
            const { template, nextTodo } = replaceTodo(markup);
            const nextCalendar = template.content.querySelector('#calendar');
            const currentCalendar = document.getElementById('calendar');
            if (nextCalendar && currentCalendar) currentCalendar.replaceWith(nextCalendar);
            const selectedDate = nextTodo.querySelector('input[name="due_date"]')?.value;
            if (selectedDate) {
              const calendar = document.getElementById('calendar');
              calendar.querySelectorAll('.calendar-day.is-selected').forEach((day) => day.classList.remove('is-selected'));
              const selectedLink = calendar.querySelector(`a[href*="todo_date=${selectedDate}"]`);
              if (selectedLink) selectedLink.classList.add('is-selected');
              window.history.replaceState({}, '', `/?month=${selectedDate.slice(0, 7)}&todo_date=${selectedDate}#todo`);
            }
          } catch (error) {
            form.submit();
          } finally {
            if (submitter && submitter.isConnected) submitter.disabled = false;
          }
        });
})();
