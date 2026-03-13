(function () {
    var root = document.getElementById('voucher-stats-root');
    if (!root) return;

    var timelineUrl = root.dataset.timelineUrl;
    var comparisonUrl = root.dataset.comparisonUrl;
    var rampupUrl = root.dataset.rampupUrl;

    var COLORS = {
        primary:   'rgba(54, 162, 235, 1)',
        primaryBg: 'rgba(54, 162, 235, 0.15)',
        orange:    'rgba(255, 159, 64, 1)',
        orangeBg:  'rgba(255, 159, 64, 0.15)',
        gray:      'rgba(150, 150, 150, 1)',
        grayBg:    'rgba(150, 150, 150, 0.1)',
    };

    function hideLoading(loadingId, canvasId) {
        document.getElementById(loadingId).style.display = 'none';
        document.getElementById(canvasId).style.display = 'block';
    }

    var chartsLoaded = false;

    function loadCharts() {
        if (chartsLoaded) return;
        chartsLoaded = true;

        fetch(timelineUrl)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                hideLoading('timeline-loading', 'timelineChart');
                new Chart(document.getElementById('timelineChart'), {
                    type: 'line',
                    data: {
                        labels: data.labels,
                        datasets: [
                            {
                                label: root.dataset.labelCumulative,
                                data: data.cumulative,
                                borderColor: COLORS.primary,
                                backgroundColor: COLORS.primaryBg,
                                fill: true,
                                tension: 0.3,
                            },
                            {
                                label: root.dataset.labelDaily,
                                data: data.daily,
                                borderColor: COLORS.orange,
                                backgroundColor: COLORS.orangeBg,
                                fill: false,
                                tension: 0.2,
                                borderDash: [5, 3],
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        interaction: { mode: 'index', intersect: false },
                        scales: {
                            x: { title: { display: true, text: root.dataset.labelDate } },
                            y: { title: { display: true, text: root.dataset.labelTickets }, beginAtZero: true },
                        },
                    },
                });
            })
            .catch(function () {
                document.getElementById('timeline-loading').innerHTML =
                    '<span class="text-danger">' + root.dataset.labelError + '</span>';
            });

        fetch(comparisonUrl)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                hideLoading('comparison-loading', 'comparisonChart');
                new Chart(document.getElementById('comparisonChart'), {
                    type: 'bar',
                    data: {
                        labels: data.labels,
                        datasets: [
                            {
                                label: root.dataset.labelThisVoucher,
                                data: data.this_voucher,
                                backgroundColor: COLORS.primary,
                                stack: 'stacked',
                            },
                            {
                                label: root.dataset.labelOtherVouchers,
                                data: data.other_vouchers,
                                backgroundColor: COLORS.orange,
                                stack: 'stacked',
                            },
                            {
                                label: root.dataset.labelNoVoucher,
                                data: data.no_voucher,
                                backgroundColor: COLORS.gray,
                                stack: 'stacked',
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        interaction: { mode: 'index', intersect: false },
                        scales: {
                            x: { stacked: true, title: { display: true, text: root.dataset.labelDate } },
                            y: { stacked: true, title: { display: true, text: root.dataset.labelTickets }, beginAtZero: true },
                        },
                    },
                });
            })
            .catch(function () {
                document.getElementById('comparison-loading').innerHTML =
                    '<span class="text-danger">' + root.dataset.labelError + '</span>';
            });

        fetch(rampupUrl)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var loadingEl = document.getElementById('rampup-loading');
                if (!data.vouchers || data.vouchers.length === 0) {
                    loadingEl.innerHTML = '<span class="text-muted">' + root.dataset.labelNoRampupData + '</span>';
                    return;
                }
                loadingEl.style.display = 'none';
                document.getElementById('rampupChart').style.display = 'block';

                var PALETTE = [
                    'rgba(54,  162, 235, 1)',
                    'rgba(75,  192, 100, 1)',
                    'rgba(255, 159,  64, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 205,  86, 1)',
                    'rgba(201, 203, 207, 1)',
                    'rgba(255, 128,   0, 1)',
                ];
                var paletteIdx = 0;
                var datasets = data.vouchers.map(function (v) {
                    var isThis = v.is_this;
                    var c = isThis ? 'rgba(255, 99, 132, 1)' : PALETTE[paletteIdx++ % PALETTE.length];
                    return {
                        label: v.code + (v.tag ? ' (' + v.tag + ')' : ''),
                        data: v.points,
                        borderColor: c,
                        backgroundColor: c.replace(', 1)', isThis ? ', 0.2)' : ', 0.05)'),
                        borderWidth: isThis ? 2.5 : 1,
                        fill: false,
                        tension: 0.3,
                        parsing: { xAxisKey: 'x', yAxisKey: 'y' },
                        order: isThis ? 0 : 1,
                    };
                });

                new Chart(document.getElementById('rampupChart'), {
                    type: 'line',
                    data: { datasets: datasets },
                    options: {
                        responsive: true,
                        interaction: { mode: 'index', intersect: false },
                        plugins: { legend: { display: false } },
                        scales: {
                            x: {
                                type: 'linear',
                                title: { display: true, text: root.dataset.labelDaysBefore },
                                min: -30, max: 0,
                                ticks: {
                                    stepSize: 5,
                                    callback: function (v) {
                                        return v === 0 ? root.dataset.labelEventDay : v;
                                    },
                                },
                            },
                            y: {
                                title: { display: true, text: root.dataset.labelTickets },
                                beginAtZero: true,
                            },
                        },
                    },
                });
            })
            .catch(function () {
                document.getElementById('rampup-loading').innerHTML =
                    '<span class="text-danger">' + root.dataset.labelError + '</span>';
            });
    }

    // Bootstrap 3 fires tab events via jQuery, not native DOM events
    if (typeof $ !== 'undefined') {
        $('#stats-tab').on('shown.bs.tab', loadCharts);
    } else {
        // Fallback: poll until jQuery is available
        var attempts = 0;
        var poll = setInterval(function () {
            if (typeof $ !== 'undefined') {
                clearInterval(poll);
                $('#stats-tab').on('shown.bs.tab', loadCharts);
            } else if (++attempts > 20) {
                clearInterval(poll);
            }
        }, 100);
    }

    // If statistics tab is already active on page load, load charts immediately
    if (root.dataset.activeTab === 'statistics') {
        loadCharts();
    }
})();
