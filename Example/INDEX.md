# Example catalogue

Ordinary Python inputs. Loops and Benchmarks are source-only; generate their readable Cython outputs on demand under ignored Test_Run/Examples. See [README.md](README.md), [historical verification](VERIFICATION.md) and [Manifest.json](Manifest.json).

## Quick start

| Python input | Purpose |
|---|---|
| [Quick_Start](Quick_Start.py) | A small runnable example: no PyCeler decorators, type annotations or Cython declarations. |

## Benchmarks

| Python input | Purpose |
|---|---|
| [Cellular_Automaton](Benchmarks/Cellular_Automaton.py) | Repeated cellular automaton generations on a nested list grid. |
| [Diffusion_3D](Benchmarks/Diffusion_3D.py) | Three-dimensional list-grid diffusion at the original benchmark size. |
| [Fluid](Benchmarks/Fluid.py) | Fluid-like grid pipeline with stencils, scalar powers and diagnostics. |
| [Image_Pipeline](Benchmarks/Image_Pipeline.py) | Image pipeline with clamped convolution, histograms, pyramid reductions and median filtering. |
| [Integer_Branches](Benchmarks/Integer_Branches.py) | Original integer-heavy nested loops, branches and bitwise checksum. |
| [Integer_Eligibility](Benchmarks/Integer_Eligibility.py) | Preserved integer eligibility reproduction with the original workload size. |
| [List_Grid_Simulation](Benchmarks/List_Grid_Simulation.py) | Repeated list-grid updates with separate current and next state. |
| [Matrix_Multiplication](Benchmarks/Matrix_Multiplication.py) | Ordinary triple-loop list matrix multiplication. |
| [Mixed_Workload](Benchmarks/Mixed_Workload.py) | Large mixed image, geometry, simulation and metrics benchmark. |
| [Monte_Carlo](Benchmarks/Monte_Carlo.py) | Monte Carlo option-payoff workload with ordered random draws. |
| [NBody](Benchmarks/NBody.py) | N-body forces, integration, energies, momentum and spatial analysis. |
| [Numerical_Simulation](Benchmarks/Numerical_Simulation.py) | Preserved numerical simulation used for generalization checks. |
| [Particle_Simulation](Benchmarks/Particle_Simulation.py) | Preserved particle simulation used for generalization checks. |
| [Ray_Tracing](Benchmarks/Ray_Tracing.py) | Ray/sphere intersections, lighting and pixel-result construction. |
| [Scalar_Math_Simulation](Benchmarks/Scalar_Math_Simulation.py) | Nested scalar math simulation with ordered energy and checksum updates. |
| [Segmented_Primes](Benchmarks/Segmented_Primes.py) | Segmented prime sieve with dependent marking and checksum accumulation. |
| [Sparse_Graph](Benchmarks/Sparse_Graph.py) | Sparse graph pipeline with indirect indices, reductions and label propagation. |

## Loops

| Python input | Purpose |
|---|---|
| [ABI_Loops](Loops/ABI_Loops.py) | Focused abi loops workload; ordinary Python inputs include supported and retained cases. |
| [Affine_Alias_Cases](Loops/Affine_Alias_Cases.py) | Focused affine alias cases workload; ordinary Python inputs include supported and retained cases. |
| [Array_Extrema_Loops](Loops/Array_Extrema_Loops.py) | Focused array extrema loops workload; ordinary Python inputs include supported and retained cases. |
| [Array_Power_Loops](Loops/Array_Power_Loops.py) | Focused array power loops workload; ordinary Python inputs include supported and retained cases. |
| [Array_Random_Loops](Loops/Array_Random_Loops.py) | Focused array random loops workload; ordinary Python inputs include supported and retained cases. |
| [Array_Region_Loops](Loops/Array_Region_Loops.py) | Focused array region loops workload; ordinary Python inputs include supported and retained cases. |
| [Branch_Bindings](Loops/Branch_Bindings.py) | Focused branch bindings workload; ordinary Python inputs include supported and retained cases. |
| [Classic_Dependencies](Loops/Classic_Dependencies.py) | Focused classic dependencies workload; ordinary Python inputs include supported and retained cases. |
| [Classic_Transport_Loops](Loops/Classic_Transport_Loops.py) | Focused classic transport loops workload; ordinary Python inputs include supported and retained cases. |
| [Complete_Array_Loops](Loops/Complete_Array_Loops.py) | Focused complete array loops workload; ordinary Python inputs include supported and retained cases. |
| [Coverage_Loops](Loops/Coverage_Loops.py) | Focused coverage loops workload; ordinary Python inputs include supported and retained cases. |
| [Diagnostic_Loops](Loops/Diagnostic_Loops.py) | Focused diagnostic loops workload; ordinary Python inputs include supported and retained cases. |
| [Dynamic_Scalar_Strides](Loops/Dynamic_Scalar_Strides.py) | Focused dynamic scalar strides workload; ordinary Python inputs include supported and retained cases. |
| [Expanded_Numeric_Loops](Loops/Expanded_Numeric_Loops.py) | Focused expanded numeric loops workload; ordinary Python inputs include supported and retained cases. |
| [Fast_Binary_Loops](Loops/Fast_Binary_Loops.py) | Focused fast binary loops workload; ordinary Python inputs include supported and retained cases. |
| [Fast_Erf_Loops](Loops/Fast_Erf_Loops.py) | Focused fast erf loops workload; ordinary Python inputs include supported and retained cases. |
| [Fast_Math_Loops](Loops/Fast_Math_Loops.py) | Focused fast math loops workload; ordinary Python inputs include supported and retained cases. |
| [Generalization_Regions](Loops/Generalization_Regions.py) | Focused generalization regions workload; ordinary Python inputs include supported and retained cases. |
| [Generated_Scalar](Loops/Generated_Scalar.py) | Focused generated scalar workload; ordinary Python inputs include supported and retained cases. |
| [Hard_Optimization_Loops](Loops/Hard_Optimization_Loops.py) | Focused hard optimization loops workload; ordinary Python inputs include supported and retained cases. |
| [Helper_Call_Cases](Loops/Helper_Call_Cases.py) | Focused helper call cases workload; ordinary Python inputs include supported and retained cases. |
| [Helper_Local_Loops](Loops/Helper_Local_Loops.py) | Focused helper local loops workload; ordinary Python inputs include supported and retained cases. |
| [Integer_Array_Loops](Loops/Integer_Array_Loops.py) | Focused integer array loops workload; ordinary Python inputs include supported and retained cases. |
| [Iterator_Loops](Loops/Iterator_Loops.py) | Focused iterator loops workload; ordinary Python inputs include supported and retained cases. |
| [Iterator_Scope_Loops](Loops/Iterator_Scope_Loops.py) | Focused iterator scope loops workload; ordinary Python inputs include supported and retained cases. |
| [Iterator_Selection_Cases](Loops/Iterator_Selection_Cases.py) | Focused iterator selection cases workload; ordinary Python inputs include supported and retained cases. |
| [List_Grid_Loops](Loops/List_Grid_Loops.py) | Focused list grid loops workload; ordinary Python inputs include supported and retained cases. |
| [List_Runtime_Cases](Loops/List_Runtime_Cases.py) | Focused list runtime cases workload; ordinary Python inputs include supported and retained cases. |
| [Map_Loops](Loops/Map_Loops.py) | Focused map loops workload; ordinary Python inputs include supported and retained cases. |
| [Math_Library](Loops/Math_Library.py) | Focused math library workload; ordinary Python inputs include supported and retained cases. |
| [Math_Unary_Sign_Loops](Loops/Math_Unary_Sign_Loops.py) | Focused math unary sign loops workload; ordinary Python inputs include supported and retained cases. |
| [Module_Constant_Loops](Loops/Module_Constant_Loops.py) | Focused module constant loops workload; ordinary Python inputs include supported and retained cases. |
| [Module_Nested_Loops](Loops/Module_Nested_Loops.py) | Focused module nested loops workload; ordinary Python inputs include supported and retained cases. |
| [Module_Scalar_Loops](Loops/Module_Scalar_Loops.py) | Focused module scalar loops workload; ordinary Python inputs include supported and retained cases. |
| [Monitoring_Cases](Loops/Monitoring_Cases.py) | Focused monitoring cases workload; ordinary Python inputs include supported and retained cases. |
| [Nested_Scope_Cases](Loops/Nested_Scope_Cases.py) | Focused nested scope cases workload; ordinary Python inputs include supported and retained cases. |
| [Numeric_Extensions](Loops/Numeric_Extensions.py) | Focused numeric extensions workload; ordinary Python inputs include supported and retained cases. |
| [Numeric_Loops](Loops/Numeric_Loops.py) | Focused numeric loops workload; ordinary Python inputs include supported and retained cases. |
| [Numeric_Region_Loops](Loops/Numeric_Region_Loops.py) | Focused numeric region loops workload; ordinary Python inputs include supported and retained cases. |
| [Parallel_Reductions](Loops/Parallel_Reductions.py) | Focused parallel reductions workload; ordinary Python inputs include supported and retained cases. |
| [Random_Bound_Cases](Loops/Random_Bound_Cases.py) | Focused random bound cases workload; ordinary Python inputs include supported and retained cases. |
| [Random_Bound_Loops](Loops/Random_Bound_Loops.py) | Focused random bound loops workload; ordinary Python inputs include supported and retained cases. |
| [Random_Boundary_Cases](Loops/Random_Boundary_Cases.py) | Focused random boundary cases workload; ordinary Python inputs include supported and retained cases. |
| [Ranking_Loops](Loops/Ranking_Loops.py) | Focused ranking loops workload; ordinary Python inputs include supported and retained cases. |
| [Readable_Pyx_Loops](Loops/Readable_Pyx_Loops.py) | Focused readable pyx loops workload; ordinary Python inputs include supported and retained cases. |
| [Readonly_Selection_Cases](Loops/Readonly_Selection_Cases.py) | Focused readonly selection cases workload; ordinary Python inputs include supported and retained cases. |
| [Readonly_Storage_Loops](Loops/Readonly_Storage_Loops.py) | Focused readonly storage loops workload; ordinary Python inputs include supported and retained cases. |
| [Region_Tail_Loops](Loops/Region_Tail_Loops.py) | Focused region tail loops workload; ordinary Python inputs include supported and retained cases. |
| [Scalar_Arithmetic](Loops/Scalar_Arithmetic.py) | Focused scalar arithmetic workload; ordinary Python inputs include supported and retained cases. |
| [Scalar_Control](Loops/Scalar_Control.py) | Focused scalar control workload; ordinary Python inputs include supported and retained cases. |
| [Scalar_Eligibility](Loops/Scalar_Eligibility.py) | Focused scalar eligibility workload; ordinary Python inputs include supported and retained cases. |
| [Scalar_Flow](Loops/Scalar_Flow.py) | Focused scalar flow workload; ordinary Python inputs include supported and retained cases. |
| [Scalar_Math_Loops](Loops/Scalar_Math_Loops.py) | Focused scalar math loops workload; ordinary Python inputs include supported and retained cases. |
| [Scalar_Promotion_Cases](Loops/Scalar_Promotion_Cases.py) | Focused scalar promotion cases workload; ordinary Python inputs include supported and retained cases. |
| [Scalar_Regions](Loops/Scalar_Regions.py) | Focused scalar regions workload; ordinary Python inputs include supported and retained cases. |
| [Shape_Only_Loops](Loops/Shape_Only_Loops.py) | Focused shape only loops workload; ordinary Python inputs include supported and retained cases. |
| [Static_Only_Loops](Loops/Static_Only_Loops.py) | Focused static only loops workload; ordinary Python inputs include supported and retained cases. |
| [Storage_Composition_Cases](Loops/Storage_Composition_Cases.py) | Focused storage composition cases workload; ordinary Python inputs include supported and retained cases. |
| [Structural_Loops](Loops/Structural_Loops.py) | Focused structural loops workload; ordinary Python inputs include supported and retained cases. |
| [Wrapped_Index_Cases](Loops/Wrapped_Index_Cases.py) | Focused wrapped index cases workload; ordinary Python inputs include supported and retained cases. |
