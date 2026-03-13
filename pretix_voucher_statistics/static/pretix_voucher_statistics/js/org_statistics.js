(function () {
    var root = document.getElementById('org-stats-root');
    if (!root) return;

    var dataUrl = root.dataset.dataUrl;
    var selectedEvents = JSON.parse(root.dataset.selectedEvents);

    if (!selectedEvents.length) return;

    var params = selectedEvents.map(function (s) {
        return 'events=' + encodeURIComponent(s);
    }).join('&');

    var PALETTE = [
        'rgba(54,  162, 235, 1)',
        'rgba(255, 99,  132, 1)',
        'rgba(75,  192, 100, 1)',
        'rgba(255, 159, 64,  1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 205, 86,  1)',
        'rgba(201, 203, 207, 1)',
        'rgba(255, 128, 0,   1)',
    ];
    var PALETTEbg = PALETTE.map(function (c) { return c.replace(', 1)', ', 0.15)'); });

    function color(i) { return PALETTE[i % PALETTE.length]; }
    function colorBg(i) { return PALETTEbg[i % PALETTEbg.length]; }

    function hideLoading(loadingId, canvasId) {
        document.getElementById(loadingId).style.display = 'none';
        document.getElementById(canvasId).style.display = 'block';
    }

    var labels = {
        date:          root.dataset.labelDate,
        cumulative:    root.dataset.labelCumulative,
        daysBeforeEvent: root.dataset.labelDaysBefore,
        eventDay:      root.dataset.labelEventDay,
        totalTickets:  root.dataset.labelTotalTickets,
        topVouchers:   root.dataset.labelTopVouchers,
        noVouchers:    root.dataset.labelNoVouchers,
        code:          root.dataset.labelCode,
        tag:           root.dataset.labelTag,
        tickets:       root.dataset.labelTickets,
        pct:           root.dataset.labelPct,
        error:         root.dataset.labelError,
        loading:       root.dataset.labelLoading,
    };

    // --- Timeline chart ---
    fetch(dataUrl + '?' + params + '&type=timeline')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            hideLoading('timeline-loading', 'timelineChart');

            var allDates = new Set();
            Object.values(data).forEach(function (ev) {
                ev.labels.forEach(function (d) { allDates.add(d); });
            });
            var dateLabels = Array.from(allDates).sort();

            var datasets = Object.entries(data).map(function (entry, i) {
                var ev = entry[1];
                var lookup = {};
                ev.labels.forEach(function (d, idx) { lookup[d] = ev.cumulative[idx]; });

                var last = 0;
                var values = dateLabels.map(function (d) {
                    if (lookup[d] !== undefined) last = lookup[d];
                    return last;
                });

                return {
                    label: ev.name,
                    data: values,
                    borderColor: color(i),
                    backgroundColor: colorBg(i),
                    fill: false,
                    tension: 0.3,
                };
            });

            new Chart(document.getElementById('timelineChart'), {
                type: 'line',
                data: { labels: dateLabels, datasets: datasets },
                options: {
                    responsive: true,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        x: { title: { display: true, text: labels.date } },
                        y: { title: { display: true, text: labels.cumulative }, beginAtZero: true },
                    },
                },
            });
        })
        .catch(function () {
            document.getElementById('timeline-loading').innerHTML =
                '<span class="text-danger">' + labels.error + '</span>';
        });

    // --- Days before event chart ---
    fetch(dataUrl + '?' + params + '&type=days_before')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            hideLoading('days-before-loading', 'daysBeforeChart');

            var datasets = Object.entries(data).map(function (entry, i) {
                var ev = entry[1];
                return {
                    label: ev.name + ' (' + ev.date_from + ')',
                    data: ev.points,
                    borderColor: color(i),
                    backgroundColor: colorBg(i),
                    fill: false,
                    tension: 0.3,
                    parsing: { xAxisKey: 'x', yAxisKey: 'y' },
                };
            });

            new Chart(document.getElementById('daysBeforeChart'), {
                type: 'line',
                data: { datasets: datasets },
                options: {
                    responsive: true,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        x: {
                            type: 'linear',
                            title: { display: true, text: labels.daysBeforeEvent },
                            min: -30,
                            max: 0,
                            ticks: {
                                stepSize: 5,
                                callback: function (v) {
                                    return v === 0 ? labels.eventDay : v;
                                },
                            },
                        },
                        y: {
                            title: { display: true, text: labels.cumulative },
                            beginAtZero: true,
                        },
                    },
                },
            });
        })
        .catch(function () {
            document.getElementById('days-before-loading').innerHTML =
                '<span class="text-danger">' + labels.error + '</span>';
        });

    // --- Leaderboards ---
    fetch(dataUrl + '?' + params + '&type=leaderboard')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var container = document.getElementById('leaderboard-section');
            var html = '';

            Object.entries(data).forEach(function (entry) {
                var ev = entry[1];
                html += '<div class="panel panel-default">';
                html += '<div class="panel-heading"><strong>' + labels.topVouchers + ': ' + ev.name + '</strong>';
                html += ' <span class="text-muted"><small>' + ev.total + ' ' + labels.totalTickets + '</small></span></div>';

                if (ev.vouchers.length === 0) {
                    html += '<div class="panel-body text-muted">' + labels.noVouchers + '</div>';
                } else {
                    html += '<div class="table-responsive"><table class="table table-condensed">';
                    html += '<thead><tr><th>#</th><th>' + labels.code + '</th><th>' + labels.tag + '</th>';
                    html += '<th>' + labels.tickets + '</th><th>' + labels.pct + '</th><th></th></tr></thead><tbody>';

                    ev.vouchers.forEach(function (v, idx) {
                        var barWidth = Math.max(2, Math.min(100, v.pct));
                        html += '<tr>';
                        html += '<td class="text-muted">' + (idx + 1) + '</td>';
                        html += '<td><code>' + v.code + '</code></td>';
                        html += '<td>' + (v.tag || '—') + '</td>';
                        html += '<td>' + v.count + '</td>';
                        html += '<td>' + v.pct + '%</td>';
                        html += '<td style="width:120px"><div class="progress" style="margin-bottom:0">';
                        html += '<div class="progress-bar" style="width:' + barWidth + '%"></div></div></td>';
                        html += '</tr>';
                    });

                    html += '</tbody></table></div>';
                }
                html += '</div>';
            });

            container.innerHTML = html;
        })
        .catch(function () {
            document.getElementById('leaderboard-section').innerHTML =
                '<div class="alert alert-danger">' + labels.error + '</div>';
        });
})();
