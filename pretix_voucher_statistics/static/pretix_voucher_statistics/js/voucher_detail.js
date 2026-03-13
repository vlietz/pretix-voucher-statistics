(function () {
    var root = document.getElementById('voucher-stats-root');
    if (!root) return;

    var timelineUrl = root.dataset.timelineUrl;
    var comparisonUrl = root.dataset.comparisonUrl;

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
