
void __cdecl16near FUN_15fd_22c0(undefined2 param_1,undefined2 param_2)

{
  int iVar1;
  undefined2 in_BX;
  int *unaff_SI;
  undefined2 unaff_DS;
  int in_stack_00000000;
  int iVar2;
  
  FUN_15fd_0f90();
  iVar2 = 0x7e;
  FUN_15fd_0f90(in_BX);
  *(undefined2 *)0x96 = 0x72;
  FUN_15fd_0ef6();
  iVar1 = *unaff_SI;
  FUN_15fd_0f75();
  *(int *)0x96 = iVar2;
  do {
    FUN_15fd_0ef6(iVar1);
    FUN_15fd_2248(iVar1 + 0xc);
    FUN_15fd_0f0d();
    iVar1 = in_stack_00000000 + -1;
  } while (iVar1 != 0);
  FUN_15fd_0ef6();
  FUN_15fd_0f75();
  *(undefined2 *)0x96 = param_2;
  FUN_15fd_0f0d();
  do {
    FUN_15fd_0ef6();
    FUN_15fd_2248();
    FUN_15fd_0f0d();
  } while (iVar2 != 1);
  return;
}

