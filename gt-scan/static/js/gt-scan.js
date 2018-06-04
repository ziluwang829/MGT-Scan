// Create variables for the target and off-target tables.
var tTable = null;
var oTable = null;

// Column names and tooltip vales for tables
var offTargetMismatchTooltip = "The number of mismatches between the potential off-target and the candidate target selected in the menu above.You can sort on multiple criteria by holding the shift-key down while selecting each additional sorting criterion.";

var mismatchTooltip = "The number of potential off-targets, for zero to three mismatches, between the candidate target and a potential off-target.<br>Click a column heading to sort the table by that column.<br>Shift click subsequent column headings for multi-column sorting.";

var oTableColumns = [
  {"title":"Potential Off-target Sequence","orderable":false,"className":"sequence","tooltip":"The sequence of the potential off-target. Mismatches to the candidate target are <b>bold</b>."},
  {"title":"Total","tooltip":"The total number of mismatches in low-specificity or high-specificity positions."},
  {"title":"High","tooltip":"The number of mismatches in high-specificity positions."},
  {"title":"Low","tooltip":"The number of mismatches in low-specificity positions."},
  {"title":"Chr","tooltip":"The name of the chromosome (reference strand) of the potential off-target."},
  {"title":"Position","tooltip":"The position of the potential off-target in the chromosome (1-based)."},
  {"title":"Str","tooltip":"The strand where the potential off-target is present. + for reference strand, - for reverse-complement of reference strand."},
  {"title":"GC","tooltip":"The GC nucleotide percentage of the potential off-target."},
  {"title":"Browser","orderable":false,"tooltip":"Click a link to view the potential off-target on the Ensembl genome browser."}
];

var tTableColumns = [
  {"title":"Position", "tooltip":"The position of the candidate target within the candidate region (1-based)."},
  {"title":"Strand","tooltip":"The candidate sequence strand that the candidate target is present in.<br> + for given strand,<br> - for reverse complement."},
  {"title":"Candidate Target Sequence","orderable":false,"className":"sequence", "tooltip":"The nucleotide sequence of the candidate target.<br>High-specificity characters (<span class=copyright>ACTGX</span>) are orange, low-specificity characters (<span class=copyright>actgx</span>) are blue and <span class=copyright>N</span> characters are green."},
  {"title":"Exact Match", "tooltip":"The number of potential off-targets that exactly match the candidate target."},
  {"title":"1 Mismatch", "tooltip":"The number of potential off-targets that match the candidate target except at one position."},
  {"title":"2 Mismatches", "tooltip":"The number of potential off-targets that match the candidate target except at two positions."},
  {"title":"3 Mismatches", "tooltip":"The number of potential off-targets that match the candidate target except at three positions."},
];


/* Maps the table header of visible columns back to the aaData/aoColumns index
This allows tooltip from offTargetColumns to be displayed in a tooltip, on hover.
From Fabian's triplex inspector */
//$.fn.dataTableExt.oApi.fnGetTh  = function ( oSettings, iTh ) {
//  var counter = -1
//  var visIndex = 0
//  for (visIndex=0;visIndex<oSettings.aoColumns.length;++visIndex) {
//    if (oSettings.aoColumns[visIndex]["bVisible"]) {
//      ++counter;
//    } 
//    if (counter == iTh) {
//      break;
//    } 
//  }
//  return visIndex;
//}


/* returns specified GET value */
(function($) {
    $.QueryString = (function(a) {
        if (a == "") return {};
        var b = {};
        for (var i = 0; i < a.length; ++i)
        {
            var p=a[i].split('=');
            if (p.length != 2) continue;
            b[p[0]] = decodeURIComponent(p[1].replace(/\+/g, " "));
        }
        return b;
    })(window.location.search.substr(1).split('&'))
})(jQuery);


/* On page ready function.
Creates the tables and allows selecting.. */
$(document).ready(function() {
  var targetUrl = "../api/" + jobId + "/targets/";

  tTable = $('#candidate-target-table').DataTable( {
    ajax: targetUrl,
    autoWidth: false,
    columns: tTableColumns,
    dom: '<"H"<"title-tt">frl>t<"F"ip>',
    jQueryUI: true,
    lengthMenu:[[10,25,50,-1],[10,25,50,"All"]],
    order: [[3,"asc"],[4,"asc"],[5,"asc"],[6,"asc"]],
    pagingType: "full_numbers",
    processing: false
  } );
 
  oTable = $('#off-target-table').DataTable( {
    autoWidth:false,
    columns: oTableColumns,
    data: [],
    dom: '<"H"<"title-ot">frl>t<"F"ip>',
    jQueryUI: true,
    lengthMenu:[[10,25,50,-1],[10,25,50,"All"]],
    order:[[1,"asc"],[2,"asc"],[3,"asc"]],
    pagingType: "full_numbers",
    processing: true,
  } );
 
  // Titles for tables
  $(".title-tt").html("<span>Candidate Targets</span><span class=helper style='background:#2d89ef;float:right;margin:7px 0 0 10px' title='Select a candidate target to view its potential off-targets.<br>Hover your pointer over a column heading to view more information.<br>You can sort on multiple criteria by holding the shift-key down while selecting each additional sorting criterion.'>?</span>")
  $(".title-ot").html("<span>Potential Off-targets</span><span class=helper style='background:#2d89ef;float:right;margin:7px 0 0 10px' title='This table shows all the off-targets passing the off-target filter and high-affinity mismatch limit for the candidate target you select in the Candidate Targets table.<br>You can sort on multiple criteria by holding the shift-key down while selecting each additional sorting criterion.'>?</span>")

  // Allows tooltips to the target table header.
  $('#candidate-target-table thead tr th').each( function(i) {
    if (i < 3) {
      //this.setAttribute( 'title', tTableColumns[tTable.fnGetTh(i)]["tooltip"] );
    } else if (i == 3) {
      //this.setAttribute( 'title', mismatchTooltip );
    } else {
      //this.setAttribute( 'title', tTableColumns[tTable.fnGetTh(i-1)]["tooltip"] );
    };
  } );
  $('#candidate-target-table thead tr th[title]').tooltip( {
    offset: [10, 0],predelay:700,effect:'slide',position: 'bottom center'
  } );

  /* and again for off-targets */
  $('#off-target-table thead tr th').each( function(i) {
    if (i == 0) {
      //this.setAttribute( 'title', oTableColumns[tTable.fnGetTh(i)]["tooltip"] );
    } else if (i == 1) {
      //this.setAttribute( 'title', offTargetMismatchTooltip );
    } else if (i < 6) {
      //this.setAttribute( 'title', oTableColumns[tTable.fnGetTh(i+2)]["tooltip"] );
    } else if (i == 6) {
      //this.setAttribute( 'title', "Click a link to view the potential off-target on the Ensembl genome browser." );
    } else {
      //this.setAttribute( 'title', oTableColumns[tTable.fnGetTh(i-6)]["tooltip"] );
    };
  } );
  $('#off-target-table thead tr th[title]').tooltip( {
    offset: [10, 0],predelay:700,effect:'slide'
  } );

  // Define click handler for target table.
  // Highlights selected and loads offtarget data
  $('#candidate-target-table tbody').on( 'click', 'tr', function () {
    var row = tTable.row(this).data();
    var targetId = row[0];
    var strand = row[1];
    if (strand == "-") {
      targetId = "-" + targetId;
    }
    tTable.$('tr.row_selected').removeClass('row_selected');
    $(this).addClass('row_selected');
    if(typeof(online) == 'undefined' ) {
      oTable.fnClearTable();
      oTable.fnAddData(offTargetData[targetId]);
    } else {
      var formattedTableURL = '../api/' + jobId + '/targets/' + targetId + '/'
      oTable.ajax.url( formattedTableURL ).load();
    }
  } );
} );


$(".time").each(function() {
  var dateString = new Date(parseInt($(this).text(), 10));
  $(this).text(dateString.toLocaleString() + " - ");
});

/* Tooltip initializer, results in the 'title' tag in .helper being displayed as a tooltip on hover */
$(function() {
  $('.helper').tooltip( {
    predelay: 200,effect: 'fade',fadeOutSpeed: 100,position: 'center right',offset: [20, 5]
  } );
} );
